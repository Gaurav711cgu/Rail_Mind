from typing import Dict, Any, Tuple
from app.agents.base_agent import BaseAgent

class DispatchAgent(BaseAgent):
    """
    Computes hold/proceed resolutions to minimize net delay.
    If recommendation confidence < 0.85, triggers manual Tier-2 escalation to human controller.
    """
    def __init__(self):
        super().__init__("DispatchAgent")
        self.auto_execute_threshold = 0.85

    async def process(self, state: Dict[str, Any]) -> Tuple[Dict[str, Any], float, str]:
        disruptions = state.get("disruptions", [])
        recommendations = state.get("recommendations", [])
        
        if not disruptions or recommendations:
            return {}, 1.0, "No dynamic recommendations required."
            
        self.log("Formulating operational dispatch resolution...")
        active_disp = disruptions[0]
        
        # Hold Coal Freight at loop to prioritize Shatabdi
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
            "is_approved": False
        }
        
        updates = {
            "recommendations": recommendations + [new_recommendation]
        }
        
        if rec_confidence < self.auto_execute_threshold:
            self.log("Confidence below threshold. Escalating to local Section Controller (Tier 2).")
            updates["escalated"] = True
            reasoning = f"Escalated HOLD recommendation issued for BOXN-902. Confidence {rec_confidence} is below the auto-execute threshold of {self.auto_execute_threshold}."
        else:
            reasoning = f"Auto-approved hold recommendation for BOXN-902. Confidence {rec_confidence} >= {self.auto_execute_threshold}."
            
        return updates, rec_confidence, reasoning
