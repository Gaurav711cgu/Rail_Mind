"""
RailRadar API client — comprehensive wrapper for all available endpoints.
Base URL: https://api.railradar.in/v1
Auth:     Authorization: Bearer <key>
Rate:     50 req/day, 10 req/min (free tier)
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.config import settings

_QUOTA_CODES = {429, 403, 503, 509}
_MAX_RETRIES = 3
_BASE_BACKOFF = 1.0
_MAX_BACKOFF = 30.0


async def _request(client: httpx.AsyncClient, method: str, path: str, **kwargs) -> Optional[dict]:
    """Shared retry-with-backoff helper. Returns parsed data payload or None."""
    for attempt in range(_MAX_RETRIES):
        try:
            resp = await client.request(method, path, **kwargs)

            if resp.status_code in _QUOTA_CODES:
                wait = min(_BASE_BACKOFF * (2**attempt) + random.uniform(0, 1), _MAX_BACKOFF)
                print(
                    f"[RailRadar] HTTP {resp.status_code} on {path!r}. "
                    f"Attempt {attempt + 1}/{_MAX_RETRIES}, backoff {wait:.1f}s."
                )
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(wait)
                    continue
                return None

            if resp.status_code != 200:
                return None

            body = resp.json()
            if not body.get("success", True):
                print(f"[RailRadar] success=false on {path!r}: {body}")
                return None
            return body.get("data", body)

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            wait = min(_BASE_BACKOFF * (2**attempt) + random.uniform(0, 1), _MAX_BACKOFF)
            print(f"[RailRadar] Network error on {path!r}: {exc}. Backoff {wait:.1f}s.")
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(wait)
            else:
                return None
        except Exception as exc:
            print(f"[RailRadar] Unexpected error on {path!r}: {exc}")
            return None
    return None


class RailRadarClient:
    """Async client covering all RailRadar v1 endpoints."""

    def __init__(self) -> None:
        key = getattr(settings, "RAILRADAR_API_KEY", "")
        base = getattr(settings, "RAILRADAR_BASE_URL", "https://api.railradar.in/v1")
        self._client = httpx.AsyncClient(
            base_url=base,
            headers={"Authorization": f"Bearer {key}"},
            timeout=12.0,
        )

    # ─── Train endpoints ────────────────────────────────────────

    async def get_train(self, number: str, halts_only: bool = False) -> Optional[dict]:
        """
        GET /v1/trains/{number}[?haltsOnly=true]
        Full schedule & stops for a train.
        Returns: { train: {...}, route: [...] }
        """
        params: dict[str, Any] = {}
        if halts_only:
            params["haltsOnly"] = "true"
        return await _request(self._client, "GET", f"/trains/{number}", params=params)

    async def get_live_status(self, number: str) -> Optional[dict]:
        """
        GET /v1/trains/{number}/live
        Real-time position, delay, and per-stop status.
        Returns: { trainNumber, trainName, status, currentLocation, delayMinutes,
                   nextHalt, isLive, trackingMode, route, train, ... }
        """
        return await _request(self._client, "GET", f"/trains/{number}/live")

    async def get_route(
        self, number: str, fmt: str = "geojson", stops: bool = True
    ) -> Optional[dict]:
        """
        GET /v1/trains/{number}/route?format=geojson&stops=true
        GeoJSON polyline + stop coordinates for a train.
        Returns: { trainNumber, format, stops: [{sequence, code, name, lat, lng}], geojson }
        """
        return await _request(
            self._client,
            "GET",
            f"/trains/{number}/route",
            params={"format": fmt, "stops": "true" if stops else "false"},
        )

    async def get_trains_between(
        self, from_code: str, to_code: str, date: Optional[str] = None
    ) -> list:
        """
        GET /v1/trains/between/{from}/{to}[?date=YYYY-MM-DD]
        All trains running between two station codes.
        Returns list of train entries.
        """
        params = {}
        if date:
            params["date"] = date
        data = await _request(
            self._client, "GET", f"/trains/between/{from_code}/{to_code}", params=params
        )
        if not data:
            return []
        return data.get("trains", data) if isinstance(data, dict) else data

    # ─── Station endpoints ──────────────────────────────────────

    async def get_station_trains(self, code: str) -> list:
        """
        GET /v1/stations/{code}/trains
        All trains halting at a station with scheduled times.
        Returns list of train-stop entries.
        """
        data = await _request(self._client, "GET", f"/stations/{code}/trains")
        if not data:
            return []
        return data.get("trains", []) if isinstance(data, dict) else data

    async def get_station_live(self, code: str, hours: int = 4) -> Optional[dict]:
        """
        GET /v1/stations/{code}/live?hours=N
        Live arrivals/departures board for a station (up to `hours` ahead).
        Returns: { station, window, trains: [{train, liveStatus, scheduledArrival, ...}] }
        """
        return await _request(
            self._client, "GET", f"/stations/{code}/live", params={"hours": hours}
        )

    # ─── Lookup endpoints ───────────────────────────────────────

    async def lookup_trains(self) -> dict:
        """
        GET /v1/lookup/trains
        Flat number → name map for all trains (useful for client-side search).
        Returns: { "12002": "Rani Kamalapati Shatabdi Express", ... }
        """
        data = await _request(self._client, "GET", "/lookup/trains")
        return data if isinstance(data, dict) else {}

    async def lookup_stations(self) -> dict:
        """
        GET /v1/lookup/stations
        Flat code → name map for all stations.
        Returns: { "NDLS": "NEW DELHI", ... }
        """
        data = await _request(self._client, "GET", "/lookup/stations")
        return data if isinstance(data, dict) else {}

    # ─── Legacy endpoints ───────────────────────────────────────

    async def legacy_trains_between(self, from_code: str, to_code: str) -> list:
        """
        GET /v1/legacy/trains/between?from=X&to=Y
        Legacy trains-between endpoint (different schema than v1).
        Returns list from data.trains.
        """
        data = await _request(
            self._client,
            "GET",
            "/legacy/trains/between",
            params={"from": from_code, "to": to_code},
        )
        if not data:
            return []
        return data.get("trains", []) if isinstance(data, dict) else data

    async def legacy_get_train(self, number: str, data_type: str = "full") -> Optional[dict]:
        """
        GET /v1/legacy/trains/{number}?dataType=full
        Legacy train schema with runningDaysBitmap, zone, etc.
        Returns: { train: { trainNumber, trainName, type, zone, runningDays, ... }, route: [...] }
        """
        return await _request(
            self._client,
            "GET",
            f"/legacy/trains/{number}",
            params={"dataType": data_type},
        )

    async def find_trains_near(self, source: str, lat: float, lng: float) -> list:
        """
        GET /v1/legacy/modules/shipping/find-trains?source=X&lat=Y&lng=Z
        Find nearest stations + trains given a GPS coordinate.
        Returns: [{ stationCode, stationName, distanceKm, totalTrains, trains: [...] }]
        """
        data = await _request(
            self._client,
            "GET",
            "/legacy/modules/shipping/find-trains",
            params={"source": source, "lat": lat, "lng": lng},
        )
        if not data:
            return []
        return data if isinstance(data, list) else data.get("stations", [])

    async def legacy_all_trains_kv(self) -> dict:
        """
        GET /v1/legacy/trains/all-kvs
        Complete train number→name KV store.
        """
        data = await _request(self._client, "GET", "/legacy/trains/all-kvs")
        return data if isinstance(data, dict) else {}

    async def legacy_all_stations_kv(self) -> dict:
        """
        GET /v1/legacy/stations/all-kvs
        Complete station code→name KV store.
        """
        data = await _request(self._client, "GET", "/legacy/stations/all-kvs")
        return data if isinstance(data, dict) else {}

    # ─── Convenience helpers ────────────────────────────────────

    def normalize_live(self, number: str, data: dict) -> dict:
        """
        Convert a RailRadar /live response to the RailMind TrainPosition schema
        used throughout the app (same shape as NTESClient output).
        """
        loc = data.get("currentLocation") or {}
        train_info = data.get("train") or {}
        return {
            "train_no": number,
            "train_name": train_info.get("name") or data.get("trainName", f"Train {number}"),
            "current_station": str(loc.get("stationCode", "UNKNOWN")).upper(),
            "current_delay": max(0, int(data.get("delayMinutes", 0) or 0)),
            "status": _map_status(str(loc.get("status") or data.get("status", "RUNNING"))),
            "next_halt": (data.get("nextHalt") or {}).get("stationCode"),
            "is_live": data.get("isLive", False),
            "tracking_mode": data.get("trackingMode", "unknown"),
            "source": "RAILRADAR",
            "data_quality": 0.95,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    async def close(self) -> None:
        await self._client.aclose()


def _map_status(raw: str) -> str:
    """Map RailRadar status strings → RailMind canonical values."""
    r = raw.upper()
    mapping = {
        "AT-STATION": "ARRIVED",
        "AT STATION": "ARRIVED",
        "RUNNING": "RUNNING",
        "NOT-STARTED": "SCHEDULED",
        "NOT STARTED": "SCHEDULED",
        "YET TO START": "SCHEDULED",
        "COMPLETED": "COMPLETED",
        "TERMINATED": "COMPLETED",
        "DEPARTED": "RUNNING",
    }
    for key, val in mapping.items():
        if key in r:
            return val
    return "RUNNING"


# Module-level singleton
railradar_client = RailRadarClient()
