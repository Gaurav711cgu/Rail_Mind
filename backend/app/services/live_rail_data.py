import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.config import settings
from app.services.rapidapi_irctc import rapidapi_irctc


STATION_COORDINATES: Dict[str, Dict[str, float | str]] = {
    "NDLS": {"name": "New Delhi", "latitude": 28.643, "longitude": 77.222},
    "GZB": {"name": "Ghaziabad", "latitude": 28.672, "longitude": 77.436},
    "ALJN": {"name": "Aligarh", "latitude": 27.892, "longitude": 78.078},
    "CNB": {"name": "Kanpur Central", "latitude": 26.448, "longitude": 80.350},
    "BVI": {"name": "Borivali", "latitude": 19.229, "longitude": 72.857},
    "ST": {"name": "Surat", "latitude": 21.205, "longitude": 72.841},
    "BRC": {"name": "Vadodara Jn", "latitude": 22.312, "longitude": 73.181},
    "ADI": {"name": "Ahmedabad Jn", "latitude": 23.027, "longitude": 72.601},
    "MMCT": {"name": "Mumbai Central", "latitude": 18.971, "longitude": 72.820},
    "SBC": {"name": "KSR Bengaluru", "latitude": 12.978, "longitude": 77.572},
    "BWT": {"name": "Bangarapet", "latitude": 12.969, "longitude": 78.204},
    "JTJ": {"name": "Jolarpettai", "latitude": 12.571, "longitude": 78.580},
    "MAS": {"name": "Chennai Central", "latitude": 13.082, "longitude": 80.275},
}


def _first_present(source: Dict[str, Any], keys: List[str]) -> Any:
    for key in keys:
        if key in source and source[key] not in (None, ""):
            return source[key]
    return None


def _walk_dicts(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, dict):
        found_dict = [value]
        for nested in value.values():
            found_dict.extend(_walk_dicts(nested))
        return found_dict
    if isinstance(value, list):
        found_list: List[Dict[str, Any]] = []
        for item in value:
            found_list.extend(_walk_dicts(item))
        return found_list
    return []


def _extract_delay(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    match = re.search(r"-?\d+", str(value))
    return max(0, int(match.group(0))) if match else 0


def _station_code_from_text(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value).upper()
    for code in STATION_COORDINATES:
        if re.search(rf"\b{re.escape(code)}\b", text):
            return code
    tokens = re.findall(r"\b[A-Z]{2,5}\b", text)
    return tokens[0] if tokens else None


class LiveRailDataService:
    def watchlist(self) -> List[str]:
        return [
            train_no.strip()
            for train_no in settings.LIVE_TRAIN_WATCHLIST.split(",")
            if train_no.strip()
        ]

    async def search_station(self, query: str) -> Dict[str, Any]:
        return await rapidapi_irctc.get("/api/v1/searchStation", {"query": query})

    async def search_train(self, query: str) -> Dict[str, Any]:
        return await rapidapi_irctc.get("/api/v1/searchTrain", {"query": query})

    async def live_status(self, train_no: str, start_day: int = 0) -> Dict[str, Any]:
        return await rapidapi_irctc.get(
            "/api/v1/liveTrainStatus",
            {"trainNo": train_no, "startDay": start_day},
        )

    async def train_schedule(self, train_no: str) -> Dict[str, Any]:
        return await rapidapi_irctc.get(
            "/api/v1/getTrainSchedule", {"trainNo": train_no}
        )

    def normalize_train_status(
        self,
        train_no: str,
        provider_payload: Dict[str, Any],
        fallback: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        data = provider_payload.get("data", provider_payload)
        dicts = _walk_dicts(data)
        merged: Dict[str, Any] = {}
        for item in dicts:
            merged.update(
                {key: value for key, value in item.items() if value not in (None, "")}
            )

        fallback = fallback or {}
        station_hint = _first_present(
            merged,
            [
                "current_station_code",
                "currentStationCode",
                "current_station",
                "currentStation",
                "station_code",
                "stationCode",
                "station",
                "source_stn_code",
                "fromStationCode",
            ],
        )
        current_station = (
            _station_code_from_text(station_hint)
            or fallback.get("current_station")
            or "UNKNOWN"
        )
        coords = STATION_COORDINATES.get(current_station, {})
        fallback_lat = fallback.get("latitude", 0.0)
        fallback_lng = fallback.get("longitude", 0.0)

        return {
            "train_no": str(
                _first_present(
                    merged, ["train_no", "trainNo", "train_number", "trainNumber"]
                )
                or train_no
            ),
            "train_name": str(
                _first_present(merged, ["train_name", "trainName", "name"])
                or fallback.get("train_name")
                or f"Train {train_no}"
            ),
            "current_station": current_station,
            "current_delay": _extract_delay(
                _first_present(
                    merged,
                    [
                        "delay",
                        "delay_min",
                        "delayMinutes",
                        "late_by",
                        "lateBy",
                        "current_delay",
                    ],
                )
                or fallback.get("current_delay")
            ),
            "status": str(
                _first_present(
                    merged,
                    ["status", "running_status", "runningStatus", "current_status"],
                )
                or fallback.get("status")
                or "LIVE"
            ).upper(),
            "latitude": float(coords.get("latitude", fallback_lat)),
            "longitude": float(coords.get("longitude", fallback_lng)),
            "data_source": provider_payload.get(
                "provider", settings.LIVE_DATA_PROVIDER
            ),
            "data_quality": 0.95 if current_station != "UNKNOWN" else 0.65,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "raw_provider_path": provider_payload.get("path"),
        }

    async def live_train_snapshot(
        self,
        train_no: str,
        fallback: Optional[Dict[str, Any]] = None,
        start_day: int = 0,
    ) -> Dict[str, Any]:
        payload = await self.live_status(train_no, start_day=start_day)
        return self.normalize_train_status(train_no, payload, fallback=fallback)

    async def live_watchlist_snapshot(
        self, fallback_trains: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        if not fallback_trains:
            from app.core.scenario_engine import scenario_engine

            fallback_trains = scenario_engine.get_state().get("trains", [])

        fallback_by_train = {
            str(train["train_no"]): train
            for train in fallback_trains or []
            if train.get("train_no")
        }
        train_numbers = list(
            dict.fromkeys([*fallback_by_train.keys(), *self.watchlist()])
        )
        live_trains: List[Dict[str, Any]] = []
        failures: List[str] = []

        for train_no in train_numbers:
            try:
                live_trains.append(
                    await self.live_train_snapshot(
                        train_no, fallback=fallback_by_train.get(train_no)
                    )
                )
            except Exception as exc:
                # Catch any Exception (HTTPException, connection error, etc.) to ensure complete resilience
                status_code = getattr(exc, "status_code", 500)
                failures.append(f"{train_no}: {status_code}")
                if fallback_by_train.get(train_no):
                    stale = dict(fallback_by_train[train_no])
                    stale["data_source"] = "scenario-fallback"
                    stale["data_quality"] = 0.25
                    stale["status"] = f"STALE_{stale.get('status', 'UNKNOWN')}"
                    live_trains.append(stale)

        if settings.REAL_DATA_REQUIRED and failures:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "Live train data is required but one or more RapidAPI calls failed.",
                    "failures": failures,
                },
            )

        return live_trains

    async def hydrate_scenario_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if (
            settings.SCENARIO_MODE
            and not settings.REAL_DATA_REQUIRED
            and not settings.RAPIDAPI_IRCTC_KEY
        ):
            return state

        live_trains = await self.live_watchlist_snapshot(state.get("trains", []))
        hydrated = dict(state)
        hydrated["trains"] = live_trains
        hydrated["telemetry_source"] = settings.LIVE_DATA_PROVIDER
        hydrated["telemetry_mode"] = "live-rapidapi"
        hydrated["scenario_mode"] = settings.SCENARIO_MODE
        hydrated["logs"] = [
            f"[MonitorAgent] Live RapidAPI telemetry hydrated for {len(live_trains)} trains.",
            *state.get("logs", []),
        ]
        return hydrated


live_rail_data = LiveRailDataService()
