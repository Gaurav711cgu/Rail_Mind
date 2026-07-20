import httpx
from datetime import date, datetime, timezone
from typing import Optional
from app.config import settings

# ─── Source priority chain ─────────────────────────────────────
# 1. NTES (free, no key, ~30 req/min)
# 2. RailwayAPI.in (500 req/day free, key required)
# 3. PostgreSQL telemetry cache (stale but real, always available)
# ───────────────────────────────────────────────────────────────

NTES_BASE = "https://enquiry.indianrail.gov.in/mntes"
RAILWAYAPI_BASE = "https://api.railwayapi.com/v2"

NTES_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://enquiry.indianrail.gov.in/",
    "X-Requested-With": "XMLHttpRequest",
}


class NTESClient:
    def __init__(self):
        self._ntes = httpx.AsyncClient(
            base_url=NTES_BASE,
            headers=NTES_HEADERS,
            timeout=10.0,
            follow_redirects=True,
        )
        # Note: getattr handles cases where RAILWAYAPI_KEY might not be present in settings initially
        api_key = getattr(settings, "RAILWAYAPI_KEY", "")
        self._railwayapi = httpx.AsyncClient(
            base_url=RAILWAYAPI_BASE,
            timeout=10.0,
            headers={"apikey": api_key} if api_key else {},
        )
        self._validated = False  # set True after first successful call
        self._field_map: dict = {}  # populated after validation

    # ── Public API ──────────────────────────────────────────────

    async def get_live_status(self, train_no: str) -> Optional[dict]:
        """
        Fetch live status. Tries NTES → RailwayAPI → DB cache in order.
        Returns None only if all three fail.
        """
        # Source 1: NTES
        result = await self._ntes_live_status(train_no)
        if result:
            await self._cache_to_db(train_no, result, source="NTES")
            return result

        # Source 2: RailwayAPI.in
        if getattr(settings, "RAILWAYAPI_KEY", ""):
            result = await self._railwayapi_live_status(train_no)
            if result:
                await self._cache_to_db(train_no, result, source="RAILWAYAPI")
                return result

        # Source 3: DB cache (stale but real)
        result = await self._db_cache_fetch(train_no)
        if result:
            result["source"] = "CACHE"
            result["data_quality"] = 0.5
            return result

        return None

    async def get_trains_between_stations(self, from_code: str, to_code: str) -> list:
        """Get trains between two stations. NTES only (no RailwayAPI equivalent on free tier)."""
        try:
            today = date.today().strftime("%Y%m%d")
            resp = await self._ntes.get(
                "/getTrainBetweenStation",
                params={
                    "fromStation": from_code,
                    "toStation": to_code,
                    "date": today,
                    "flexiWithDate": "Y",
                },
            )
            if resp.status_code == 200:
                body = resp.json()
                # Handle both list and dict responses
                if isinstance(body, list):
                    return body
                return body.get("trainBtwnStnsList", body.get("trains", []))
        except Exception as e:
            print(f"[NTES] Trains between stations failed: {e}")
        return []

    async def validate_endpoints(self) -> dict:
        """
        Run at startup. Confirms which endpoints are live.
        Results stored in settings for the session.
        """
        results = {
            "ntes_live_status": False,
            "ntes_between_stations": False,
            "railwayapi": False,
        }
        try:
            resp = await self._ntes.get(
                "/getNTESTrainLiveStatus",
                params={"trainNo": "12301", "date": date.today().strftime("%Y%m%d")},
            )
            results["ntes_live_status"] = (
                resp.status_code == 200
                and "application/json" in resp.headers.get("content-type", "")
            )
        except Exception:
            pass

        try:
            resp = await self._ntes.get(
                "/getTrainBetweenStation",
                params={
                    "fromStation": "NDLS",
                    "toStation": "CNB",
                    "date": date.today().strftime("%Y%m%d"),
                    "flexiWithDate": "Y",
                },
            )
            results["ntes_between_stations"] = resp.status_code == 200
        except Exception:
            pass

        if getattr(settings, "RAILWAYAPI_KEY", ""):
            try:
                resp = await self._railwayapi.get("/live-train-status/12301/0")
                results["railwayapi"] = resp.status_code == 200
            except Exception:
                pass

        self._validated = any(results.values())
        print(f"[NTESClient] Validation: {results}")
        return results

    # ── Private source implementations ─────────────────────────

    async def _ntes_live_status(self, train_no: str) -> Optional[dict]:
        try:
            resp = await self._ntes.get(
                "/getNTESTrainLiveStatus",
                params={"trainNo": train_no, "date": date.today().strftime("%Y%m%d")},
            )
            if resp.status_code != 200:
                return None
            ct = resp.headers.get("content-type", "")
            if "json" not in ct:
                # Got HTML — endpoint changed
                print(f"[NTES] Endpoint returned HTML for {train_no}. Endpoint may have changed.")
                return None
            raw = resp.json()
            return self._normalize_ntes(train_no, raw)
        except Exception as e:
            print(f"[NTES] _ntes_live_status failed for {train_no}: {e}")
            return None

    async def _railwayapi_live_status(self, train_no: str) -> Optional[dict]:
        try:
            resp = await self._railwayapi.get(f"/live-train-status/{train_no}/0")
            if resp.status_code != 200:
                return None
            raw = resp.json()
            return self._normalize_railwayapi(train_no, raw)
        except Exception as e:
            print(f"[RailwayAPI] Failed for {train_no}: {e}")
            return None

    def _normalize_ntes(self, train_no: str, raw: dict) -> Optional[dict]:
        """
        Convert NTES response to RailMind TrainPosition schema.
        Defensive: tries multiple field name variants.
        Returns None if critical fields missing.
        """
        # NTES wraps data in different keys depending on version
        body = raw
        if isinstance(raw, dict):
            for key in ("trainLiveStatusList", "data", "response", "train"):
                if key in raw:
                    val = raw[key]
                    body = val[0] if isinstance(val, list) and val else val
                    break

        if not body or not isinstance(body, dict):
            return None

        # Try all known field name variants
        def get_first(*keys):
            for k in keys:
                if k in body and body[k] not in (None, "", "null"):
                    return body[k]
            return None

        station = get_first(
            "stationCode",
            "station_code",
            "currentStationCode",
            "current_station_code",
            "stnCode",
            "code",
        )
        delay_raw = get_first(
            "delayInMins", "delay", "lateBy", "delay_min", "late_by", "delayMinutes"
        )
        name = get_first("trainName", "train_name", "name", "trainNameDisplay")
        status = get_first(
            "trainRunningStatus", "running_status", "status", "currentStatus", "runStatus"
        )

        if not station:
            return None  # Can't place the train without station

        try:
            delay = max(0, int(str(delay_raw).replace("min", "").strip())) if delay_raw else 0
        except (ValueError, TypeError):
            delay = 0

        return {
            "train_no": train_no,
            "train_name": str(name or f"Train {train_no}"),
            "current_station": str(station).upper(),
            "current_delay": delay,
            "status": self._map_running_status(str(status or "")),
            "source": "NTES",
            "data_quality": 0.9,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def _normalize_railwayapi(self, train_no: str, raw: dict) -> Optional[dict]:
        """Normalize RailwayAPI.in response to RailMind schema."""
        data = raw.get("result", raw.get("data", raw))
        if not isinstance(data, dict):
            return None

        station = data.get("current_station_code", data.get("station", "UNKNOWN"))
        delay = max(0, int(data.get("delay", data.get("late_by", 0)) or 0))

        return {
            "train_no": train_no,
            "train_name": str(data.get("train_name", f"Train {train_no}")),
            "current_station": str(station).upper(),
            "current_delay": delay,
            "status": self._map_running_status(str(data.get("status", "RUNNING"))),
            "source": "RAILWAYAPI",
            "data_quality": 0.85,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def _map_running_status(self, raw: str) -> str:
        raw_upper = raw.upper()
        mapping = {
            "YET TO START": "SCHEDULED",
            "NOT STARTED": "SCHEDULED",
            "RUNNING": "RUNNING",
            "ON TIME": "RUNNING",
            "ARRIVED": "ARRIVED",
            "AT STATION": "ARRIVED",
            "DEPARTED": "RUNNING",
            "LEFT": "RUNNING",
            "REACHED DESTINATION": "COMPLETED",
            "TERMINATED": "COMPLETED",
        }
        for key, val in mapping.items():
            if key in raw_upper:
                return val
        return "RUNNING"  # safe default

    async def _cache_to_db(self, train_no: str, data: dict, source: str):
        """Persist to train_telemetry_cache table."""
        import json

        try:
            from app.db.database import AsyncSessionLocal
            from sqlalchemy import text

            async with AsyncSessionLocal() as session:
                await session.execute(
                    text("""
                        INSERT INTO train_telemetry_cache (train_no, payload, source, fetched_at)
                        VALUES (:train_no, :payload, :source, NOW())
                        ON CONFLICT (train_no)
                        DO UPDATE SET payload = :payload, source = :source, fetched_at = NOW()
                    """),
                    {"train_no": train_no, "payload": json.dumps(data), "source": source},
                )
                await session.commit()
        except Exception as e:
            print(f"[NTESClient] Cache write failed for {train_no}: {e}")

    async def _db_cache_fetch(self, train_no: str) -> Optional[dict]:
        """Fetch from cache. Returns None if no entry within 6 hours."""
        import json

        try:
            from app.db.database import AsyncSessionLocal
            from sqlalchemy import text

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT payload FROM train_telemetry_cache
                        WHERE train_no = :train_no
                        AND fetched_at > NOW() - INTERVAL '6 hours'
                        LIMIT 1
                    """),
                    {"train_no": train_no},
                )
                row = result.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception as e:
            print(f"[NTESClient] Cache read failed for {train_no}: {e}")
        return None

    async def close(self):
        await self._ntes.aclose()
        await self._railwayapi.aclose()


ntes_client = NTESClient()
