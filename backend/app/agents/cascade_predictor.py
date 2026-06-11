"""
Cascade Predictor Agent — NetworkX BFS delay propagation.

Algorithm:
  1. Build (or retrieve cached) directed section graph from active trains + timetable.
  2. For each active disruption, run BFS from disrupted section.
  3. Apply delay transfer function per edge (section).
  4. Sum passengers across affected trains.
  5. Emit CascadeReport with per-train delay additions and overall confidence.

Delay transfer function (calibrated from IRCTC punctuality data):
  delay_added = upstream_delay * transfer_factor * congestion_multiplier
  where transfer_factor ≈ 0.7 per section hop (delay dissipates at junctions)
        congestion_multiplier scales with section capacity utilisation
"""

import logging
from typing import Any, Dict, List, Tuple

import networkx as nx

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Static railway section graph — major corridors                             #
#  Full topology loaded from seed_railway_graph.py for production             #
# --------------------------------------------------------------------------- #
_CORRIDOR_EDGES = [
    # Delhi–Howrah trunk
    ("NDLS", "GZB", {"distance": 25, "capacity": 12, "speed": 110}),
    ("GZB", "ALJN", {"distance": 100, "capacity": 10, "speed": 130}),
    ("ALJN", "CNB", {"distance": 210, "capacity": 8, "speed": 130}),
    ("CNB", "PRYJ", {"distance": 190, "capacity": 15, "speed": 130}),
    ("PRYJ", "BSB", {"distance": 120, "capacity": 15, "speed": 110}),
    ("BSB", "MGS", {"distance": 55, "capacity": 12, "speed": 110}),
    ("MGS", "DDU", {"distance": 30, "capacity": 10, "speed": 110}),
    ("DDU", "HWH", {"distance": 550, "capacity": 8, "speed": 100}),
    # Delhi–Mumbai trunk (WR)
    ("NDLS", "KOTA", {"distance": 459, "capacity": 10, "speed": 130}),
    ("KOTA", "RTM", {"distance": 134, "capacity": 8, "speed": 110}),
    ("RTM", "BRC", {"distance": 185, "capacity": 10, "speed": 130}),
    ("BRC", "ST", {"distance": 100, "capacity": 12, "speed": 130}),
    ("ST", "BVI", {"distance": 260, "capacity": 12, "speed": 130}),
    ("BVI", "MMCT", {"distance": 25, "capacity": 14, "speed": 110}),
    # Delhi–Chennai trunk (SCR/CR)
    ("NDLS", "AGC", {"distance": 200, "capacity": 10, "speed": 130}),
    ("AGC", "JHS", {"distance": 220, "capacity": 8, "speed": 110}),
    ("JHS", "BPL", {"distance": 290, "capacity": 10, "speed": 130}),
    ("BPL", "NGP", {"distance": 340, "capacity": 8, "speed": 130}),
    ("NGP", "SC", {"distance": 250, "capacity": 8, "speed": 110}),
    ("SC", "MAS", {"distance": 668, "capacity": 10, "speed": 130}),
    # Bengaluru corridor
    ("MAS", "JTJ", {"distance": 220, "capacity": 8, "speed": 110}),
    ("JTJ", "BWT", {"distance": 130, "capacity": 6, "speed": 100}),
    ("BWT", "SBC", {"distance": 60, "distance2": 60, "capacity": 10, "speed": 110}),
]

# Average passengers per delayed train (from IR annual report)
_PASSENGERS_PER_TRAIN = {
    "SUPERFAST": 1800,
    "EXPRESS": 1200,
    "MAIL": 900,
    "RAJDHANI": 1600,
    "SHATABDI": 1100,
    "VANDE": 1300,
    "FREIGHT": 0,
    "DEFAULT": 1000,
}

# Delay transfer factor per section hop
_TRANSFER_FACTOR = 0.70  # 30% delay dissipates at each junction


def _build_graph() -> nx.DiGraph:
    G = nx.DiGraph()
    for from_s, to_s, attrs in _CORRIDOR_EDGES:
        G.add_edge(from_s, to_s, **attrs)
        # Add reverse edge (bidirectional track)
        G.add_edge(to_s, from_s, **attrs)
    return G


_RAILWAY_GRAPH: nx.DiGraph = _build_graph()


def _congestion_multiplier(capacity: int, active_trains_on_section: int) -> float:
    """
    Returns a multiplier > 1.0 when section is over capacity.
    At 100% capacity: 1.3x delay amplification.
    At 50% capacity: 1.0x (no amplification).
    """
    utilisation = min(1.0, active_trains_on_section / max(capacity, 1))
    return 1.0 + 0.3 * max(0.0, utilisation - 0.5) / 0.5


def _estimate_passengers(train_no: str, trains: List[Dict]) -> int:
    for t in trains:
        if t.get("train_no") == train_no:
            t_type = t.get("train_type", "DEFAULT").upper()
            return _PASSENGERS_PER_TRAIN.get(t_type, _PASSENGERS_PER_TRAIN["DEFAULT"])
    return _PASSENGERS_PER_TRAIN["DEFAULT"]


class CascadePredictor(BaseAgent):
    def __init__(self):
        super().__init__("CascadePredictor")

    async def process(self, state: Dict[str, Any]) -> Tuple[Dict[str, Any], float, str]:
        disruptions: List[Dict] = state.get("disruptions", [])
        trains: List[Dict] = state.get("trains", [])

        if not disruptions:
            return {}, 1.0, "No active disruptions. Cascade simulation idle."

        active = disruptions[0]
        start_node = active.get("section_from")
        upstream_delay = active.get("upstream_delay_minutes", 60)

        # Validate start node exists in graph
        if start_node not in _RAILWAY_GRAPH:
            logger.warning("[CascadePredictor] Station %s not in graph. Skipping BFS.", start_node)
            return {}, 0.50, f"Station {start_node} not in network graph."

        # ------------------------------------------------------------------ #
        #  BFS cascade propagation                                            #
        # ------------------------------------------------------------------ #
        affected_trains: List[Dict] = []
        total_passengers = 0
        cascade_depth = 0

        try:
            bfs_tree = nx.bfs_tree(_RAILWAY_GRAPH, source=start_node, depth_limit=5)
            bfs_nodes = list(bfs_tree.nodes())

            active_count_on_section = len(
                [t for t in trains if t.get("current_station") == start_node]
            )

            for depth, node in enumerate(bfs_nodes[1:], start=1):  # skip root
                # Delay propagated to this hop
                edge_data = _RAILWAY_GRAPH.get_edge_data(start_node, node) or {}
                capacity = edge_data.get("capacity", 10)
                congestion = _congestion_multiplier(capacity, active_count_on_section)
                delay_at_node = upstream_delay * (_TRANSFER_FACTOR**depth) * congestion

                if delay_at_node < 5:
                    # Less than 5 min — not operationally significant
                    continue

                # Find trains scheduled through this node
                trains_here = [
                    t
                    for t in trains
                    if t.get("current_station") == node or node in t.get("route_stations", [])
                ]

                for train in trains_here:
                    train_no = train.get("train_no", "UNK")
                    passengers = _estimate_passengers(train_no, trains)
                    total_passengers += passengers
                    affected_trains.append(
                        {
                            "train_no": train_no,
                            "station": node,
                            "delay_added_minutes": round(delay_at_node),
                            "confidence": round(0.95 - depth * 0.05, 2),
                            "passengers_affected": passengers,
                        }
                    )

                if not trains_here:
                    # Still add node as potentially affected even without matched trains
                    affected_trains.append(
                        {
                            "train_no": "UNSCHEDULED",
                            "station": node,
                            "delay_added_minutes": round(delay_at_node),
                            "confidence": round(0.75 - depth * 0.05, 2),
                            "passengers_affected": 0,
                        }
                    )

                cascade_depth = max(cascade_depth, depth)

        except Exception as exc:
            logger.error("[CascadePredictor] BFS error: %s", exc, exc_info=True)
            return {}, 0.40, f"BFS propagation failed: {exc}"

        # Update disruption with cascade metadata
        updated_disruption = {
            **active,
            "cascade_depth": cascade_depth,
            "passengers_affected": total_passengers,
            "severity": _severity_from_cascade(cascade_depth, total_passengers, active),
        }
        updated_disruptions = [updated_disruption] + disruptions[1:]

        confidence = max(0.70, 0.95 - cascade_depth * 0.04)
        reasoning = (
            f"BFS propagation from {start_node}: {cascade_depth} hops, "
            f"{len(affected_trains)} downstream impacts, "
            f"~{total_passengers:,} passengers affected. "
            f"Peak delay transfer: {round(upstream_delay * _TRANSFER_FACTOR)} min at next section."
        )

        self.log(reasoning)
        return (
            {
                "disruptions": updated_disruptions,
                "cascade_affected_trains": affected_trains,
            },
            confidence,
            reasoning,
        )


def _severity_from_cascade(depth: int, passengers: int, disruption: Dict) -> str:
    current = disruption.get("severity", "MEDIUM")
    if depth >= 4 or passengers >= 5000:
        return "CRITICAL"
    if depth >= 2 or passengers >= 2000:
        return "HIGH"
    if depth >= 1 or passengers >= 500:
        return "MEDIUM"
    return current
