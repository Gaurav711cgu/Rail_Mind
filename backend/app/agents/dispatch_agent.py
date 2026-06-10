import httpx
import json
from typing import Dict, Any, Tuple
from app.agents.base_agent import BaseAgent
from app.config import settings


class DispatchAgent(BaseAgent):
    """
    Computes hold/proceed resolutions to minimize net delay.
    Uses Groq LLM (llama-3.3-70b-versatile) to dynamically compute resolutions if API key is present.
    If recommendation confidence < 0.85, triggers manual Tier-2 escalation to human controller.
    """

    def __init__(self):
        super().__init__("DispatchAgent")
        self.auto_execute_threshold = 0.85

    async def process(self, state: Dict[str, Any]) -> Tuple[Dict[str, Any], float, str]:
        disruptions = state.get("disruptions", [])
        recommendations = state.get("recommendations", [])

        if not disruptions:
            return {}, 1.0, "No dynamic recommendations required."

        self.log("Formulating operational dispatch resolution using RailMind engine...")
        active_disp = disruptions[0]

        # Default fallback heuristic recommendation
        rec_confidence = 0.78
        new_recommendation = {
            "id": f"rec-{self._generate_uuid()[:8]}",
            "disruption_id": active_disp["id"],
            "type": "HOLD",
            "target_train": "BOXN-902",
            "target_section": "GZB-ALJN loop line",
            "reasoning": "Hold Coal Freight (BOXN-902) to clear track block for high-priority Shatabdi 12002. Reduces net cascade delay by 120 minutes. Escalated due to manual check rule on freight priorities.",
            "confidence": rec_confidence,
            "tier": 2,
            "is_approved": False,
        }

        # Try calling Groq API if key is configured
        if settings.GROQ_API_KEY:
            try:
                self.log(
                    f"Querying Groq LLM ({settings.GROQ_MODEL}) for operational resolution..."
                )
                prompt = f"""
You are the Chief Section Controller for Indian Railways, operating the RailMind AI dispatch system.
An operational disruption has occurred on the network. You must issue a dispatch resolution (HOLD a lower-priority train at a loop line, or PROCEED, or ESCALATE to human).

Disruption Details:
- Affected Train: {active_disp.get("train_no", "12002")}
- Disrupted Section: {active_disp.get("section_from", "NDLS")} -> {active_disp.get("section_to", "GZB")}
- Type: {active_disp.get("disruption_type", "SIGNAL_FAILURE")}
- Severity: {active_disp.get("severity", "MEDIUM")}

All Active Trains:
{json.dumps(state.get("trains", []), indent=2)}

Generate the optimal hold/proceed decision to minimize net passenger delay minutes and keep high-priority trains moving.
Return ONLY valid JSON in this format (no extra text or markdown formatting):
{{
  "type": "HOLD",
  "target_train": "BOXN-902",
  "target_section": "GZB-ALJN loop line",
  "reasoning": "Detailed operational reasoning explaining why this action is optimal.",
  "confidence": 0.88
}}
"""
                headers = {
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a precise railway operations dispatcher. Output valid JSON only.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                }

                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    if response.status_code == 200:
                        res_json = response.json()
                        content = res_json["choices"][0]["message"]["content"]
                        self.log(f"Groq raw response content: {content}")
                        parsed_rec = json.loads(content)

                        rec_confidence = float(parsed_rec.get("confidence", 0.82))
                        new_recommendation = {
                            "id": f"rec-{self._generate_uuid()[:8]}",
                            "disruption_id": active_disp["id"],
                            "type": parsed_rec.get("type", "HOLD"),
                            "target_train": parsed_rec.get("target_train", "BOXN-902"),
                            "target_section": parsed_rec.get(
                                "target_section", "GZB-ALJN loop line"
                            ),
                            "reasoning": parsed_rec.get(
                                "reasoning",
                                "Hold Coal Freight to clear high-priority path.",
                            ),
                            "confidence": rec_confidence,
                            "tier": 1
                            if rec_confidence >= self.auto_execute_threshold
                            else 2,
                            "is_approved": False,
                        }
                        self.log(
                            "Successfully generated recommendation using Groq LLM."
                        )
                    else:
                        self.log(
                            f"Groq API returned error status {response.status_code}. Using fallback heuristic."
                        )
            except Exception as e:
                self.log(
                    f"Error querying Groq API: {str(e)}. Using fallback heuristic."
                )
        else:
            self.log("Groq API key not configured. Using fallback heuristic.")

        updates = {"recommendations": recommendations + [new_recommendation]}

        if rec_confidence < self.auto_execute_threshold:
            self.log(
                "Confidence below threshold. Escalating to local Section Controller (Tier 2)."
            )
            updates["escalated"] = True
            reasoning = f"Escalated {new_recommendation['type']} recommendation issued for {new_recommendation['target_train']}. Confidence {rec_confidence} is below the auto-execute threshold of {self.auto_execute_threshold}."
        else:
            reasoning = f"Auto-approved recommendation for {new_recommendation['target_train']}. Confidence {rec_confidence} >= {self.auto_execute_threshold}."

        return updates, rec_confidence, reasoning
