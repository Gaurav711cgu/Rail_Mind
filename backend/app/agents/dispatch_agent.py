"""
Dispatch Agent — generates HOLD/PROCEED/ESCALATE recommendations.

Uses Claude claude-sonnet-4-20250514 to reason over the current disruption state and
produce structured dispatch recommendations. Falls back to deterministic rules
when the Anthropic API is unavailable or confidence is unclear.

Confidence gating (PRD spec):
  >= 0.85 → Tier 1 (auto-recommended, logged)
  0.65–0.84 → Tier 2 (escalated to human controller)
  < 0.65 → Log only, not surfaced in UI
"""

import json
import logging
from typing import Any, Dict, List, Tuple

from app.agents.base_agent import BaseAgent
from app.config import settings

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Deterministic rules (always evaluated first)                               #
# --------------------------------------------------------------------------- #
_PASSENGER_KEYWORDS = ("SHATABDI", "RAJDHANI", "VANDE", "DURONTO", "GATIMAAN")
_SAFETY_CRITICAL_TYPES = ("SIGNAL_FAILURE", "TRACK_FAULT", "DERAILMENT")


def _is_passenger_train(train_no: str) -> bool:
    return any(k in train_no.upper() for k in _PASSENGER_KEYWORDS)


def _is_safety_critical(disruption: Dict) -> bool:
    return disruption.get("disruption_type", "") in _SAFETY_CRITICAL_TYPES


def _deterministic_recommendation(disruption: Dict, trains: List[Dict]) -> Tuple[str, str, float]:
    """
    Returns (rec_type, reasoning, confidence) using hard rules.
    Called when LLM is unavailable or as pre-filter before LLM.
    """
    if _is_safety_critical(disruption):
        return (
            "ESCALATE",
            f"Safety-critical disruption type '{disruption['disruption_type']}' "
            "requires mandatory human controller review. Auto-execution blocked.",
            0.60,  # below threshold → always Tier 2
        )

    affected_trains = [t for t in trains if t.get("current_delay", 0) > 20]
    freight = [t for t in affected_trains if t.get("train_type") == "FREIGHT"]
    passenger = [t for t in affected_trains if t.get("train_type") != "FREIGHT"]

    if freight and passenger:
        return (
            "HOLD",
            f"Hold {len(freight)} freight train(s) at nearest loop to clear path "
            f"for {len(passenger)} delayed passenger service(s). "
            "Passenger priority rule applied (IRCTC operational standard).",
            0.88,
        )
    if freight:
        return (
            "PROCEED",
            "No passenger conflicts detected. Freight trains may proceed on schedule.",
            0.92,
        )
    return (
        "ESCALATE",
        "Insufficient context for deterministic resolution. Escalating to controller.",
        0.60,
    )


# --------------------------------------------------------------------------- #
#  LLM prompt builder                                                         #
# --------------------------------------------------------------------------- #
def _build_dispatch_prompt(disruption: Dict, trains: List[Dict], cascade_info: str) -> str:
    train_summary = "\n".join(
        f"  - Train {t.get('train_no', 'UNK')} ({t.get('train_name', 'Unknown')}): "
        f"delay={t.get('current_delay', 0)}min, status={t.get('status', 'UNKNOWN')}, "
        f"at={t.get('current_station', 'UNK')}"
        for t in trains[:6]  # cap to 6 trains in prompt
    )

    return f"""You are RailMind's Dispatch Agent — an autonomous AI section controller for Indian Railways.

ACTIVE DISRUPTION:
  ID: {disruption.get("id", "N/A")}
  Train: {disruption.get("train_no", "N/A")}
  Section: {disruption.get("section_from", "?")} → {disruption.get("section_to", "?")}
  Type: {disruption.get("disruption_type", "UNKNOWN")}
  Severity: {disruption.get("severity", "UNKNOWN")}
  Cascade depth: {disruption.get("cascade_depth", 0)}

AFFECTED TRAINS:
{train_summary if train_summary else "  None identified"}

CASCADE ANALYSIS:
{cascade_info}

OPERATIONAL RULES (mandatory):
1. Passenger trains always take priority over freight at shared sections
2. Safety-critical types (SIGNAL_FAILURE, TRACK_FAULT, DERAILMENT) must ESCALATE — never auto-resolve
3. If crew duty hours are unknown, flag for relief coordination
4. SPAD (Signal Passed At Danger) risk → always ESCALATE

Based on the above, provide a dispatch recommendation as JSON with exactly these fields:
{{
  "action": "HOLD" | "PROCEED" | "REROUTE_FREIGHT" | "ESCALATE",
  "target_train": "<train_no of the train to act on>",
  "target_section": "<section identifier>",
  "reasoning": "<2-3 sentences of clear operational reasoning>",
  "confidence": <float 0.0 to 1.0>,
  "crew_alert": <true|false>,
  "estimated_delay_saving_minutes": <integer>
}}

Return ONLY the JSON object. No preamble, no markdown fences."""


# --------------------------------------------------------------------------- #
#  DispatchAgent                                                               #
# --------------------------------------------------------------------------- #
class DispatchAgent(BaseAgent):
    def __init__(self):
        super().__init__("DispatchAgent")
        self._threshold = settings.AGENT_DISPATCH_CONFIDENCE_THRESHOLD
        self._anthropic_client = None

    def _get_client(self):
        if self._anthropic_client is None and settings.ANTHROPIC_API_KEY:
            try:
                from anthropic import AsyncAnthropic

                self._anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            except ImportError:
                logger.warning("[DispatchAgent] anthropic package not installed")
        return self._anthropic_client

    async def _llm_recommend(
        self, disruption: Dict, trains: List[Dict], cascade_info: str
    ) -> Tuple[str, str, float, bool, int]:
        """
        Calls Claude claude-sonnet-4-20250514 for reasoning.
        Returns (action, reasoning, confidence, crew_alert, delay_saving).
        Raises on any API failure so caller can fall back.
        """
        client = self._get_client()
        if client is None:
            raise RuntimeError("Anthropic client unavailable")

        prompt = _build_dispatch_prompt(disruption, trains, cascade_info)

        response = await client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        # Strip markdown fences if the model adds them despite instructions
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        return (
            data.get("action", "ESCALATE"),
            data.get("reasoning", "No reasoning provided."),
            float(data.get("confidence", 0.60)),
            bool(data.get("crew_alert", False)),
            int(data.get("estimated_delay_saving_minutes", 0)),
        )

    async def process(self, state: Dict[str, Any]) -> Tuple[Dict[str, Any], float, str]:
        disruptions: List[Dict] = state.get("disruptions", [])
        trains: List[Dict] = state.get("trains", [])
        recommendations: List[Dict] = state.get("recommendations", [])

        # No disruptions → nothing to dispatch
        if not disruptions:
            return {}, 1.0, "No active disruptions. Dispatch agent idle."

        active = disruptions[0]
        cascade_info = (
            f"Cascade depth {active.get('cascade_depth', 0)}, "
            f"approx {active.get('passengers_affected', 0)} passengers affected."
        )

        # ------------------------------------------------------------------ #
        #  Safety pre-check (deterministic, non-negotiable)                  #
        # ------------------------------------------------------------------ #
        if _is_safety_critical(active):
            rec_type, reasoning, confidence = _deterministic_recommendation(active, trains)
            rec = self._build_rec(active, rec_type, reasoning, confidence, trains, False, 0)
            updates = {"recommendations": recommendations + [rec], "escalated": True}
            self.log(f"Safety-critical disruption → auto-escalated. Reason: {reasoning}")
            return updates, confidence, reasoning

        # ------------------------------------------------------------------ #
        #  Try LLM first, fall back to deterministic                         #
        # ------------------------------------------------------------------ #
        action = "ESCALATE"
        reasoning = ""
        confidence = 0.60
        crew_alert = False
        delay_saving = 0

        try:
            action, reasoning, confidence, crew_alert, delay_saving = await self._llm_recommend(
                active, trains, cascade_info
            )
            self.log(f"LLM recommendation: {action} (conf={confidence:.2f})")
        except Exception as exc:
            logger.warning("[DispatchAgent] LLM failed: %s — using deterministic rules", exc)
            action, reasoning, confidence = _deterministic_recommendation(active, trains)

        rec = self._build_rec(
            active, action, reasoning, confidence, trains, crew_alert, delay_saving
        )
        tier = 1 if confidence >= self._threshold else 2
        rec["tier"] = tier

        updates: Dict[str, Any] = {"recommendations": recommendations + [rec]}
        if tier == 2:
            updates["escalated"] = True
            self.log(
                f"Confidence {confidence:.2f} < threshold {self._threshold} → Tier 2 escalation"
            )

        return updates, confidence, reasoning

    def _build_rec(
        self,
        disruption: Dict,
        action: str,
        reasoning: str,
        confidence: float,
        trains: List[Dict],
        crew_alert: bool,
        delay_saving: int,
    ) -> Dict[str, Any]:
        import datetime

        tier = 1 if confidence >= self._threshold else 2

        # Pick target train: first delayed train in affected list, fallback to disruption train
        delayed = [t for t in trains if t.get("current_delay", 0) > 0]
        target_train = delayed[0].get("train_no") if delayed else disruption.get("train_no", "UNK")

        return {
            "id": f"rec-{self._generate_uuid()[:8]}",
            "disruption_id": disruption.get("id", ""),
            "type": action,
            "target_train": target_train,
            "target_section": f"{disruption.get('section_from', '?')}-{disruption.get('section_to', '?')}",
            "reasoning": reasoning,
            "confidence": round(confidence, 3),
            "tier": tier,
            "is_approved": False,
            "crew_alert": crew_alert,
            "estimated_delay_saving_minutes": delay_saving,
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }
