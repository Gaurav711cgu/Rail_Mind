import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from app.agents.base_agent import BaseAgent

class AuditAgent(BaseAgent):
    """
    Chronologically seals all agent events in a cryptographic hash chain.
    Prevents unauthorized tempering of explainable decision reasoning.
    """
    def __init__(self):
        super().__init__("AuditAgent")

    async def process(self, state: Dict[str, Any]) -> Tuple[Dict[str, Any], float, str]:
        self.log("Sealing audit logs...")
        logs = state.get("logs", [])
        audit_chain = state.get("audit_chain", [])
        
        # Calculate new chain hash link
        prev_hash = audit_chain[-1]["hash"] if audit_chain else "0000000000000000000000000000000000000000000000000000000000000000"
        
        # Create a new log block
        log_payload = "|".join(logs)
        current_hash = hashlib.sha256(f"{prev_hash}|{log_payload}".encode("utf-8")).hexdigest()
        
        new_block = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prev_hash": prev_hash,
            "hash": current_hash,
            "logs_count": len(logs)
        }
        
        return {
            "audit_chain": audit_chain + [new_block]
        }, 1.0, f"Sealed decision chain successfully. Current Hash block signature: {current_hash}."
