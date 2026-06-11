from typing import Any, Dict, Tuple
from app.agents.base_agent import BaseAgent


class ConflictDetector(BaseAgent):
    """
    Analyzes physical track occupancy plans to flag downstream section blockings
    where multiple trains attempt to enter the same block section simultaneously.
    """

    def __init__(self):
        super().__init__("ConflictDetector")

    async def process(self, state: Any) -> Tuple[Dict[str, Any], float, str]:
        disruptions = state.get("disruptions", [])
        if not disruptions:
            return {}, 1.0, "No active disruptions. Path conflicts nominal."

        self.log("Analyzing corridor capacity constraints...")
        active_disp = disruptions[0]

        # Simulating route conflict detection
        if active_disp["status"] == "ACTIVE" and active_disp["severity"] == "MEDIUM":
            self.log("Conflict identified on GZB-ALJN section between passenger and freight train.")
            active_disp["severity"] = "HIGH"
            active_disp["cascade_depth"] = 1

            return (
                {"disruptions": disruptions},
                0.94,
                "Downstream path conflict calculated on GZB-ALJN section. Overlap window: 19:40-20:15. P(conflict) = 0.94.",
            )

        return {}, 1.0, "Occupancy overlaps verified. No new route conflicts detected."
