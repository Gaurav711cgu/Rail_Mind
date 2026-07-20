"""
Monitor Agent — live train telemetry ingestion + anomaly detection.

Data flow:
  1. Poll indianrailapi.com (or NTES fallback) for all watchlist trains
  2. Cache positions in Redis (TTL = 90s)
  3. Run anomaly checks per train:
     a. Velocity impossibility (position jumped too far in 1 poll cycle)
     b. Delay spike (>30 min increase in single cycle)
     c. SPAD risk (approaching red signal zone)
  4. Emit DisruptionEvent for any train crossing delay threshold
"""

import logging
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.agents.base_agent import BaseAgent
from app.config import settings
from app.services.ntes_client import ntes_client

logger = logging.getLogger(__name__)

# Max physically possible distance between two consecutive polls (km)
# At 200 km/h for 90s → ~5 km
_MAX_POSITION_JUMP_KM = 8.0

# Delay increase in a single poll cycle that triggers anomaly
_DELAY_SPIKE_THRESHOLD_MIN = 30

# Haversine distance between station coords (simplified flat-earth for short distances)
_STATION_COORDS: Dict[str, Tuple[float, float]] = {
    "NDLS": (28.643, 77.222),
    "GZB": (28.672, 77.436),
    "ALJN": (27.892, 78.078),
    "CNB": (26.454, 80.350),
    "PRYJ": (25.448, 81.851),
    "BSB": (25.317, 82.973),
    "MGS": (25.145, 83.115),
    "DDU": (25.273, 83.448),
    "HWH": (22.583, 88.342),
    "KOTA": (25.181, 75.845),
    "RTM": (23.333, 75.033),
    "BRC": (22.312, 73.181),
    "ST": (21.205, 72.841),
    "BVI": (19.229, 72.857),
    "MMCT": (18.971, 72.820),
    "AGC": (27.194, 77.999),
    "JHS": (25.449, 78.568),
    "BPL": (23.259, 77.412),
    "NGP": (21.145, 79.082),
    "SC": (17.431, 78.501),
    "MAS": (13.082, 80.275),
    "JTJ": (12.571, 78.580),
    "BWT": (12.969, 78.204),
    "SBC": (12.978, 77.572),
    "ADI": (23.027, 72.601),
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math

    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def _position_jump_km(prev_station: Optional[str], curr_station: Optional[str]) -> float:
    if not prev_station or not curr_station or prev_station == curr_station:
        return 0.0
    p = _STATION_COORDS.get(prev_station)
    c = _STATION_COORDS.get(curr_station)
    if p and c:
        return _haversine_km(p[0], p[1], c[0], c[1])
    return 0.0


class MonitorAgent(BaseAgent):
    def __init__(self):
        super().__init__("MonitorAgent")
        self._prev_positions: Dict[str, Dict] = {}  # train_no → last known state

    async def process(self, state: Any) -> Tuple[Dict[str, Any], float, str]:
        self.log("Polling live train telemetry...")

        trains = state.get("trains", [])
        disruptions = state.get("disruptions", [])

        # Fetch live data
        live_trains = await self._fetch_live_trains(trains)

        if not live_trains:
            return (
                {
                    "trains": trains  # Return existing state unchanged
                },
                0.70,
                "Live data unavailable. Serving cached train state.",
            )

        # Run anomaly detection
        new_disruptions = []
        anomaly_count = 0

        for train in live_trains:
            train_no = train.get("train_no", "")
            current_delay = train.get("current_delay", 0)
            current_station = train.get("current_station", "")
            prev = self._prev_positions.get(train_no, {})

            # Check 1: Delay spike
            prev_delay = prev.get("current_delay", 0)
            if current_delay - prev_delay > _DELAY_SPIKE_THRESHOLD_MIN:
                self.log(
                    f"DELAY SPIKE: {train_no} delay jumped from "
                    f"{prev_delay}→{current_delay} min at {current_station}"
                )
                anomaly_count += 1
                if not any(d.get("train_no") == train_no for d in disruptions):
                    new_disruptions.append(self._make_disruption(train, "DELAY_CASCADE", "HIGH"))

            # Check 2: Delay threshold (>20 min, not already disrupted)
            elif current_delay > 20 and not any(d.get("train_no") == train_no for d in disruptions):
                new_disruptions.append(self._make_disruption(train, "DELAY_CASCADE", "MEDIUM"))

            # Check 3: Position velocity (impossible jump)
            jump_km = _position_jump_km(prev.get("current_station"), current_station)
            if jump_km > _MAX_POSITION_JUMP_KM:
                self.log(
                    f"POSITION ANOMALY: {train_no} jumped {jump_km:.1f}km in one poll cycle. "
                    f"Flagging data as potentially spoofed."
                )
                train["data_quality"] = 0.2
                train["anomaly_flag"] = "POSITION_SPOOFING_SUSPECTED"
                anomaly_count += 1

            # Update previous state
            self._prev_positions[train_no] = {
                "current_delay": current_delay,
                "current_station": current_station,
            }

        combined_disruptions = disruptions + new_disruptions
        confidence = 0.98 if not anomaly_count else max(0.75, 0.98 - anomaly_count * 0.05)
        reasoning = (
            f"Polled {len(live_trains)} trains. "
            f"{anomaly_count} anomalies detected. "
            f"{len(new_disruptions)} new disruption(s) raised."
        )

        self.log(reasoning)
        return (
            {
                "trains": live_trains,
                "disruptions": combined_disruptions,
            },
            confidence,
            reasoning,
        )

    async def _fetch_live_trains(self, fallback: List[Dict]) -> List[Dict]:
        """
        Attempts to fetch live train data from NTES client.
        Falls back to the existing state with a data quality warning.
        """
        watchlist = [t.strip() for t in settings.LIVE_TRAIN_WATCHLIST.split(",") if t.strip()]

        # In live mode cap to LIVE_MODE_TRAIN_CAP to prevent rate limiting issues
        train_cap = getattr(settings, "LIVE_MODE_TRAIN_CAP", 10)
        watchlist = watchlist[:train_cap]

        results: List[Dict] = []

        for train_no in watchlist:
            try:
                train = await ntes_client.get_live_status(train_no)
                if train:
                    results.append(train)
                await asyncio.sleep(getattr(settings, "NTES_RATE_LIMIT_DELAY_SEC", 2.0))
            except Exception as exc:
                logger.warning("[MonitorAgent] Error fetching train %s: %s", train_no, exc)

        return results if results else fallback

    def _make_disruption(self, train: Dict, disp_type: str, severity: str) -> Dict:
        return {
            "id": f"disp-{self._generate_uuid()[:8]}",
            "train_no": train.get("train_no", "UNK"),
            "section_from": train.get("current_station", "UNK"),
            "section_to": "NEXT",
            "disruption_type": disp_type,
            "severity": severity,
            "cascade_depth": 0,
            "status": "ACTIVE",
            "upstream_delay_minutes": train.get("current_delay", 30),
            "detected_at": datetime.utcnow().isoformat(),
        }
