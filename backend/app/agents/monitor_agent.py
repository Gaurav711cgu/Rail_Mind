from typing import Dict, Any, Tuple
from app.agents.base_agent import BaseAgent


class MonitorAgent(BaseAgent):
    """
    Ingests live telemetry streams (NTES/GPS) and compares it with scheduled timetables.
    Triggers anomalies when threshold variances are exceeded.
    """

    def __init__(self):
        super().__init__("MonitorAgent")

    async def process(self, state: Dict[str, Any]) -> Tuple[Dict[str, Any], float, str]:
        self.log("Ingesting train telemetries...")
        trains = state.get("trains", [])
        disruptions = state.get("disruptions", [])

        updates = {}
        confidence = 1.0
        reasoning = "All active trains are within schedule variance thresholds."

        # Check for delays > 20 minutes
        for t in trains:
            if t.get("current_delay", 0) > 20 and not disruptions:
                self.log(
                    f"Anomaly detected on train {t['train_no']}: current delay {t['current_delay']} min."
                )
                new_disruption = {
                    "id": f"disp-{self._generate_uuid()[:8]}",
                    "train_no": t["train_no"],
                    "section_from": t["current_station"],
                    "section_to": "GZB",  # Default downstream
                    "disruption_type": "SIGNAL_FAILURE"
                    if t["status"] == "HELD"
                    else "DELAY_CASCADE",
                    "severity": "MEDIUM",
                    "cascade_depth": 0,
                    "status": "ACTIVE",
                }
                updates["disruptions"] = disruptions + [new_disruption]
                confidence = 0.98
                reasoning = f"Train {t['train_no']} delayed by {t['current_delay']} min exceeds the 20-minute operational variance threshold at station {t['current_station']}."
                break

        return updates, confidence, reasoning
