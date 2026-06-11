"""
Audit Agent — cryptographic append-only decision ledger.

Each audit entry includes:
  - SHA-256(prev_hash | agent | action | target | reasoning | confidence | timestamp)

The chain is tamper-evident: modifying any past entry breaks all subsequent hashes.
Verification: POST /api/v1/audit/verify recomputes and compares the full chain.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64  # The known first prev_hash in the chain


def _compute_entry_hash(
    prev_hash: str,
    agent_name: str,
    action_type: str,
    target: str,
    reasoning: str,
    confidence: float,
    timestamp: str,
) -> str:
    payload = "|".join(
        [
            prev_hash,
            agent_name,
            action_type,
            target,
            reasoning[:500],  # cap to avoid unbounded input
            f"{confidence:.6f}",
            timestamp,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_chain(audit_entries: List[Dict]) -> Tuple[bool, int, str]:
    """
    Recomputes the hash chain from scratch.
    Returns (is_valid, failing_index, error_message).
    """
    if not audit_entries:
        return True, -1, "Empty chain — valid by convention."

    prev_hash = GENESIS_HASH

    for i, entry in enumerate(audit_entries):
        expected = _compute_entry_hash(
            prev_hash=prev_hash,
            agent_name=entry.get("agent", ""),
            action_type=entry.get("action", ""),
            target=entry.get("target", ""),
            reasoning=entry.get("reasoning", ""),
            confidence=float(entry.get("confidence", 0.0)),
            timestamp=entry.get("timestamp", ""),
        )
        stored = entry.get("hash", "")
        if stored != expected:
            return (
                False,
                i,
                (f"Hash mismatch at entry {i}: expected={expected[:16]}… stored={stored[:16]}…"),
            )
        prev_hash = stored

    return True, -1, "Chain intact."


class AuditAgent(BaseAgent):
    def __init__(self):
        super().__init__("AuditAgent")

    async def process(self, state: Any) -> Tuple[Dict[str, Any], float, str]:
        self.log("Sealing agent decisions into audit chain...")

        audit_chain: List[Dict] = state.get("audit_chain", [])
        recommendations: List[Dict] = state.get("recommendations", [])
        disruptions: List[Dict] = state.get("disruptions", [])

        prev_hash = audit_chain[-1]["hash"] if audit_chain else GENESIS_HASH
        new_entries: List[Dict] = []
        new_chain: List[Dict] = list(audit_chain)

        # ------------------------------------------------------------------ #
        #  Log every recommendation as an individual auditable action         #
        # ------------------------------------------------------------------ #
        for rec in recommendations:
            rec_id = rec.get("id", "UNK")
            # Skip if already audited
            if any(e.get("target") == rec_id for e in audit_chain):
                continue

            ts = datetime.now(tz=timezone.utc).isoformat()
            entry_hash = _compute_entry_hash(
                prev_hash=prev_hash,
                agent_name=rec.get("agent_name", "DispatchAgent"),
                action_type=rec.get("type", "HOLD"),
                target=rec_id,
                reasoning=rec.get("reasoning", ""),
                confidence=float(rec.get("confidence", 0.0)),
                timestamp=ts,
            )

            entry = {
                "timestamp": ts,
                "agent": rec.get("agent_name", "DispatchAgent"),
                "action": rec.get("type", "HOLD"),
                "target": rec_id,
                "reasoning": rec.get("reasoning", ""),
                "confidence": rec.get("confidence", 0.0),
                "tier": rec.get("tier", 1),
                "prev_hash": prev_hash,
                "hash": entry_hash,
            }
            new_entries.append(entry)
            new_chain.append(entry)
            prev_hash = entry_hash

        # ------------------------------------------------------------------ #
        #  Log disruption state changes                                       #
        # ------------------------------------------------------------------ #
        for disp in disruptions:
            disp_id = disp.get("id", "UNK")
            action_key = f"DISRUPTION_DETECTED:{disp_id}"
            if any(e.get("target") == action_key for e in audit_chain):
                continue

            ts = datetime.now(tz=timezone.utc).isoformat()
            entry_hash = _compute_entry_hash(
                prev_hash=prev_hash,
                agent_name="MonitorAgent",
                action_type="DISRUPTION_DETECTED",
                target=action_key,
                reasoning=(
                    f"Disruption {disp_id} detected: severity={disp.get('severity')}, "
                    f"type={disp.get('disruption_type')}, "
                    f"section={disp.get('section_from')}→{disp.get('section_to')}"
                ),
                confidence=0.98,
                timestamp=ts,
            )
            entry = {
                "timestamp": ts,
                "agent": "MonitorAgent",
                "action": "DISRUPTION_DETECTED",
                "target": action_key,
                "reasoning": (
                    f"Severity={disp.get('severity')}, "
                    f"type={disp.get('disruption_type')}, "
                    f"cascade_depth={disp.get('cascade_depth', 0)}"
                ),
                "confidence": 0.98,
                "tier": 1,
                "prev_hash": prev_hash,
                "hash": entry_hash,
            }
            new_entries.append(entry)
            new_chain.append(entry)
            prev_hash = entry_hash

        # ------------------------------------------------------------------ #
        #  Verify chain integrity after update                                #
        # ------------------------------------------------------------------ #
        chain_valid, fail_idx, err_msg = verify_chain(new_chain)
        if not chain_valid:
            logger.error(
                "[AuditAgent] CHAIN INTEGRITY FAILURE at entry %d: %s",
                fail_idx,
                err_msg,
            )

        tail_hash = new_chain[-1]["hash"] if new_chain else GENESIS_HASH
        reasoning = (
            f"Sealed {len(new_entries)} new entries. "
            f"Chain length: {len(new_chain)}. "
            f"Integrity: {'✓ valid' if chain_valid else '✗ COMPROMISED'}. "
            f"Tail hash: {tail_hash[:16]}…"
        )
        self.log(reasoning)

        return (
            {
                "audit_chain": new_chain,
                "audit_entries": new_entries,
                "audit_chain_valid": chain_valid,
            },
            1.0,
            reasoning,
        )
