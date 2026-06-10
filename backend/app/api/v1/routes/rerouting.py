from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.models.recommendation import ReroutingSuggestion, AlternativeTrain

router = APIRouter()

@router.get("", response_model=List[ReroutingSuggestion])
async def list_rerouting_suggestions(disruption_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    if settings.SCENARIO_MODE:
        # Provide suggestions matching the scenario presentation
        # Vande Bharat 22415 is offered as an alternative for Shatabdi passengers
        suggestions = [
            ReroutingSuggestion(
                id="reroute-001",
                disruption_id=disruption_id or "disp-001",
                passenger_origin="NDLS",
                passenger_destination="ALJN",
                alternatives=[
                    AlternativeTrain(
                        train_no="22415",
                        departure_station="NDLS",
                        departure_time="15:00",
                        arrival_time="16:35",
                        seat_availability="RAC 14",
                        rac_confirmation_probability=0.88,
                        connection_required=False
                    )
                ],
                advisory_text="Stranded passengers at NDLS on train 12002 are advised to transfer to Vande Bharat 22415 leaving platform 9. Confirmed probability is 88% based on historical Monday cancellation rates.",
                generated_by_agent="NotificationAgent",
                confidence=0.90,
                generated_at=datetime.utcnow()
            )
        ]
        return suggestions
    else:
        # DB query placeholder
        return []


@router.get("/network-state")
async def get_network_state():
    """Return current rail network graph as JSON for frontend visualisation."""
    NODES = ["NDLS", "GZB", "ALJN", "CNB", "PRYJ", "BSB", "HWH", "MMCT", "BRC", "MAS", "SBC", "SC"]
    EDGES = [
        {"from": "NDLS", "to": "GZB",  "weight": 5,  "distance_km": 25},
        {"from": "GZB",  "to": "ALJN", "weight": 10, "distance_km": 100},
        {"from": "ALJN", "to": "CNB",  "weight": 8,  "distance_km": 210},
        {"from": "CNB",  "to": "PRYJ", "weight": 6,  "distance_km": 190},
        {"from": "PRYJ", "to": "BSB",  "weight": 7,  "distance_km": 120},
        {"from": "BSB",  "to": "HWH",  "weight": 15, "distance_km": 635},
        {"from": "NDLS", "to": "MMCT", "weight": 30, "distance_km": 1384},
        {"from": "BRC",  "to": "MMCT", "weight": 12, "distance_km": 391},
    ]
    return {"nodes": NODES, "edges": EDGES, "total_sections": len(EDGES)}

@router.get("/{disruption_id}", response_model=ReroutingSuggestion)
async def get_rerouting_for_disruption(disruption_id: str, db: AsyncSession = Depends(get_db)):
    suggestions = await list_rerouting_suggestions(disruption_id=disruption_id, db=db)
    if not suggestions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No suggestions found for disruption {disruption_id}"
        )
    return suggestions[0]


# ── POST /rerouting/suggest ────────────────────────────────────────────────
# NetworkX shortest-path with delay-weighted edges.
# Accepts { from_station, to_station, avoid_sections?: [] }

class ReroutingRequest(BaseModel):
    from_station: str
    to_station: str
    avoid_sections: List[str] = []


@router.post("/suggest", response_model=ReroutingSuggestion)
async def suggest_reroute(req: ReroutingRequest):
    """
    Compute delay-aware shortest path using NetworkX and return an alternative
    rerouting suggestion with ranked trains.
    """
    import networkx as nx

    # ── Build weighted directed graph from known topology ────────────────
    G = nx.DiGraph()

    # (from, to, base_delay_minutes, distance_km)
    EDGES = [
        ("NDLS", "GZB",  5,  25),
        ("GZB",  "ALJN", 10, 100),
        ("ALJN", "CNB",  8,  210),
        ("CNB",  "PRYJ", 6,  190),
        ("PRYJ", "BSB",  7,  120),
        ("BSB",  "HWH",  15, 635),
        ("NDLS", "MMCT", 30, 1384),
        ("BRC",  "MMCT", 12, 391),
        ("NDLS", "MAS",  45, 2180),   # via trunk route
        ("MAS",  "SBC",  6,  360),
        ("SBC",  "SC",   4,  610),
    ]

    # Add reverse edges (Indian Railways bidirectional sections)
    for frm, to, delay, dist in EDGES:
        G.add_edge(frm, to, weight=delay, distance=dist)
        G.add_edge(to, frm, weight=delay, distance=dist)

    # Apply extra penalty for avoided sections
    for section in req.avoid_sections:
        parts = section.split("-")
        if len(parts) == 2 and G.has_edge(parts[0], parts[1]):
            G[parts[0]][parts[1]]["weight"] = 9999
            G[parts[1]][parts[0]]["weight"] = 9999

    src, dst = req.from_station.upper(), req.to_station.upper()
    if src not in G.nodes or dst not in G.nodes:
        raise HTTPException(
            status_code=422,
            detail=f"Station code '{src}' or '{dst}' not in network graph. "
                   f"Valid codes: {sorted(G.nodes)}"
        )

    try:
        path = nx.shortest_path(G, source=src, target=dst, weight="weight")
        total_delay = sum(
            G[path[i]][path[i+1]]["weight"] for i in range(len(path)-1)
        )
        total_dist = sum(
            G[path[i]][path[i+1]].get("distance", 0) for i in range(len(path)-1)
        )
    except nx.NetworkXNoPath:
        raise HTTPException(status_code=404, detail=f"No path found from {src} to {dst}")

    # ── Build alternative trains for each hop ──────────────────────────
    TRAIN_LOOKUP = {
        ("NDLS", "GZB"):  ("12309", "Rajdhani Exp",   "06:00", "06:35", "AVL 42", 0.95),
        ("NDLS", "ALJN"): ("12034", "Shatabdi Exp",   "06:15", "07:55", "RAC 8",  0.88),
        ("NDLS", "CNB"):  ("12004", "Lucknow Shata",  "06:20", "10:30", "AVL 12", 0.92),
        ("NDLS", "MMCT"): ("12952", "Mumbai Rajdhani","17:00", "07:55", "RAC 14", 0.82),
        ("GZB",  "ALJN"): ("22415", "Vande Bharat",   "14:00", "15:35", "AVL 6",  0.91),
        ("ALJN", "CNB"):  ("12034", "Shatabdi Exp",   "08:20", "10:30", "AVL 5",  0.90),
        ("CNB",  "PRYJ"): ("12801", "Purushottam Exp","22:10", "02:15", "RAC 2",  0.85),
        ("PRYJ", "BSB"):  ("13005", "Amritsar Exp",   "03:00", "05:30", "AVL 18", 0.87),
    }

    alternatives = []
    for i in range(len(path) - 1):
        key = (path[i], path[i+1])
        if key in TRAIN_LOOKUP:
            tno, tname, dep, arr, avail, prob = TRAIN_LOOKUP[key]
            alternatives.append(AlternativeTrain(
                train_no=tno,
                departure_station=path[i],
                departure_time=dep,
                arrival_time=arr,
                seat_availability=avail,
                rac_confirmation_probability=prob,
                connection_required=(i > 0),
            ))

    segments = " → ".join(path)
    advisory = (
        f"Optimal reroute via {segments} identified by NetworkX Dijkstra "
        f"(delay-weighted). "
        f"Estimated cumulative section delay: {total_delay} min over {total_dist} km. "
        f"{'Direct journey.' if len(alternatives) <= 1 else f'{len(alternatives)} connection(s) required.'}"
    )

    return ReroutingSuggestion(
        id=f"reroute-{src}-{dst}-{int(datetime.utcnow().timestamp())}",
        disruption_id="live",
        passenger_origin=src,
        passenger_destination=dst,
        alternatives=alternatives,
        advisory_text=advisory,
        generated_by_agent="ReroutingEngine(NetworkX)",
        confidence=min(0.98, 1.0 - total_delay / 500),
        generated_at=datetime.utcnow(),
    )


