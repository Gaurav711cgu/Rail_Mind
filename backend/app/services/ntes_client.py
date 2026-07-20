"""NTES / RailRadar / RailwayAPI client with exponential backoff, retry, and stale-cache fallback."""

import asyncio
import random
from datetime import date, datetime, timezone
from typing import Optional

import httpx

from app.config import settings
from app.services.railradar_client import railradar_client

# ─── Source priority chain ─────────────────────────────────────
# 1. NTES            (free, no key, ~30 req/min)
# 2. RailRadar       (50 req/day free, key required)
# 3. RailwayAPI.in   (500 req/day free, key required)
# 4. PostgreSQL DB   (stale cache, always available)
# ───────────────────────────────────────────────────────────────

NTES_BASE = "https://enquiry.indianrail.gov.in/mntes"
RAILWAYAPI_BASE = "https://api.railwayapi.com/v2"

NTES_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://enquiry.indianrail.gov.in/",
    "X-Requested-With": "XMLHttpRequest",
}

# Rate-limit / quota error status codes
_QUOTA_STATUS_CODES = {429, 403, 503, 509}

# Retry config
_MAX_RETRIES = 3
_BASE_BACKOFF = 1.0  # seconds
_MAX_BACKOFF = 30.0  # seconds cap


async def _fetch_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs,
) -> Optional[httpx.Response]:
    """Execute an httpx request with exponential backoff + jitter."""
    for attempt in range(_MAX_RETRIES):
        try:
            resp = await client.request(method, url, **kwargs)
            if resp.status_code in _QUOTA_STATUS_CODES:
                wait = min(_BASE_BACKOFF * (2**attempt) + random.uniform(0, 1), _MAX_BACKOFF)
                print(
                    f"[NTESClient] Rate-limited (HTTP {resp.status_code}) on {url!r}. "
                    f"Attempt {attempt + 1}/{_MAX_RETRIES}. Backing off {wait:.1f}s."
                )
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(wait)
                else:
                    print(f"[NTESClient] Quota exhausted after {_MAX_RETRIES} attempts.")
                    return None
                continue
            return resp
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            wait = min(_BASE_BACKOFF * (2**attempt) + random.uniform(0, 1), _MAX_BACKOFF)
            print(f"[NTESClient] Network error on {url!r}: {exc}. Backoff {wait:.1f}s.")
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(wait)
            else:
                return None
        except Exception as exc:
            print(f"[NTESClient] Unexpected error on {url!r}: {exc}.")
            return None
    return None


class NTESClient:
    def __init__(self):
        self._ntes = httpx.AsyncClient(
            base_url=NTES_BASE,
            headers=NTES_HEADERS,
            timeout=10.0,
            follow_redirects=True,
        )

        # RailwayAPI.in — tertiary fallback
        railwayapi_key = getattr(settings, "RAILWAYAPI_KEY", "")
        self._railwayapi = httpx.AsyncClient(
            base_url=RAILWAYAPI_BASE,
            timeout=10.0,
            headers={"apikey": railwayapi_key} if railwayapi_key else {},
        )

        self._validated = False
        self._field_map: dict = {}

    # ── Public API ──────────────────────────────────────────────

    async def get_live_status(self, train_no: str) -> Optional[dict]:
        """
        Fetch live status: NTES → RailRadar → RailwayAPI → DB cache (stale).
        On quota exhaustion, falls back to cached data instead of erroring out.
        """
        # Source 1: NTES
        result = await self._ntes_live_status(train_no)
        if result:
            await self._cache_to_db(train_no, result, source="NTES")
            return result

        # Source 2: RailRadar
        if getattr(settings, "RAILRADAR_API_KEY", ""):
            result = await self._railradar_live_status(train_no)
            if result:
                await self._cache_to_db(train_no, result, source="RAILRADAR")
                return result

        # Source 3: RailwayAPI.in
        if getattr(settings, "RAILWAYAPI_KEY", ""):
            result = await self._railwayapi_live_status(train_no)
            if result:
                await self._cache_to_db(train_no, result, source="RAILWAYAPI")
                return result

        # Source 4: DB cache — stale but real, always attempted on upstream failure
        print(f"[NTESClient] All live sources failed for {train_no}. Serving stale cache.")
        result = await self._db_cache_fetch(train_no)
        if result:
            result["source"] = "CACHE"
            result["data_quality"] = 0.5
            result["stale"] = True
            result["cache_notice"] = "Live API quota exhausted. Displaying last known data."
            return result

        return None

    async def get_trains_between_stations(self, from_code: str, to_code: str) -> list:
        """Get trains between two stations. Tries NTES then RailRadar."""
        # Source 1: NTES
        today = date.today().strftime("%Y%m%d")
        resp = await _fetch_with_retry(
            self._ntes,
            "GET",
            "/getTrainBetweenStation",
            params={
                "fromStation": from_code,
                "toStation": to_code,
                "date": today,
                "flexiWithDate": "Y",
            },
        )
        if resp and resp.status_code == 200:
            try:
                body = resp.json()
                trains = (
                    body
                    if isinstance(body, list)
                    else body.get("trainBtwnStnsList", body.get("trains", []))
                )
                if trains:
                    return trains
            except Exception as e:
                print(f"[NTES] Failed to parse trains-between-stations: {e}")

        # Source 2: RailRadar
        if getattr(settings, "RAILRADAR_API_KEY", ""):
            trains = await railradar_client.get_trains_between(from_code, to_code)
            if trains:
                return trains

        return []

    async def validate_endpoints(self) -> dict:
        """Run at startup. Confirms which endpoints are live."""
        results = {
            "ntes_live_status": False,
            "ntes_between_stations": False,
            "railradar": False,
            "railwayapi": False,
        }

        try:
            resp = await _fetch_with_retry(
                self._ntes,
                "GET",
                "/getNTESTrainLiveStatus",
                params={"trainNo": "12301", "date": date.today().strftime("%Y%m%d")},
            )
            results["ntes_live_status"] = bool(
                resp
                and resp.status_code == 200
                and "application/json" in resp.headers.get("content-type", "")
            )
        except Exception:
            pass

        try:
            resp = await _fetch_with_retry(
                self._ntes,
                "GET",
                "/getTrainBetweenStation",
                params={
                    "fromStation": "NDLS",
                    "toStation": "CNB",
                    "date": date.today().strftime("%Y%m%d"),
                    "flexiWithDate": "Y",
                },
            )
            results["ntes_between_stations"] = bool(resp and resp.status_code == 200)
        except Exception:
            pass

        if getattr(settings, "RAILRADAR_API_KEY", ""):
            try:
                data = await railradar_client.get_live_status("12301")
                results["railradar"] = data is not None
            except Exception:
                pass

        if getattr(settings, "RAILWAYAPI_KEY", ""):
            try:
                resp = await _fetch_with_retry(
                    self._railwayapi, "GET", "/live-train-status/12301/0"
                )
                results["railwayapi"] = bool(resp and resp.status_code == 200)
            except Exception:
                pass

        self._validated = any(results.values())
        print(f"[NTESClient] Validation: {results}")
        return results

    # ── Private source implementations ─────────────────────────

    async def _ntes_live_status(self, train_no: str) -> Optional[dict]:
        resp = await _fetch_with_retry(
            self._ntes,
            "GET",
            "/getNTESTrainLiveStatus",
            params={"trainNo": train_no, "date": date.today().strftime("%Y%m%d")},
        )
        if not resp or resp.status_code != 200:
            return None
        if "json" not in resp.headers.get("content-type", ""):
            print(f"[NTES] Endpoint returned HTML for {train_no}. Endpoint may have changed.")
            return None
        try:
            return self._normalize_ntes(train_no, resp.json())
        except Exception as e:
            print(f"[NTES] Failed to parse live status for {train_no}: {e}")
            return None

    async def _railradar_live_status(self, train_no: str) -> Optional[dict]:
        """Fetch from RailRadar /v1/trains/{number}/live via railradar_client."""
        data = await railradar_client.get_live_status(train_no)
        if not data:
            return None
        return railradar_client.normalize_live(train_no, data)

    async def _railwayapi_live_status(self, train_no: str) -> Optional[dict]:
        resp = await _fetch_with_retry(self._railwayapi, "GET", f"/live-train-status/{train_no}/0")
        if not resp or resp.status_code != 200:
            return None
        try:
            return self._normalize_railwayapi(train_no, resp.json())
        except Exception as e:
            print(f"[RailwayAPI] Failed to parse response for {train_no}: {e}")
            return None

    # ── Normalizers ─────────────────────────────────────────────

    def _normalize_ntes(self, train_no: str, raw: dict) -> Optional[dict]:
        """Convert NTES response to RailMind TrainPosition schema."""
        body = raw
        if isinstance(raw, dict):
            for key in ("trainLiveStatusList", "data", "response", "train"):
                if key in raw:
                    val = raw[key]
                    body = val[0] if isinstance(val, list) and val else val
                    break

        if not body or not isinstance(body, dict):
            return None

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
            return None

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

    def _normalize_railradar(self, train_no: str, data: dict) -> Optional[dict]:
        """
        Normalize RailRadar /v1/trains/{number}/live response to RailMind schema.
        Actual response shape (from live test):
          data.currentLocation.stationCode, data.delayMinutes,
          data.train.name, data.status, data.isLive
        """
        if not data:
            return None

        # Current location — nested object
        loc = data.get("currentLocation") or {}
        station = loc.get("stationCode") or data.get("stationCode") or "UNKNOWN"

        delay = max(0, int(data.get("delayMinutes", 0) or 0))

        train_info = data.get("train") or {}
        name = train_info.get("name") or data.get("trainName") or f"Train {train_no}"

        raw_status = loc.get("status") or data.get("status") or "RUNNING"

        return {
            "train_no": train_no,
            "train_name": str(name),
            "current_station": str(station).upper(),
            "current_delay": delay,
            "status": self._map_running_status(str(raw_status)),
            "next_halt": (data.get("nextHalt") or {}).get("stationCode"),
            "is_live": data.get("isLive", False),
            "tracking_mode": data.get("trackingMode", "unknown"),
            "source": "RAILRADAR",
            "data_quality": 0.95,
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
        return "RUNNING"

    # ── DB cache helpers ────────────────────────────────────────

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
        """
        Fetch from cache. 24-hour window maximises stale-data availability
        when all upstream quotas are exhausted.
        """
        import json

        try:
            from app.db.database import AsyncSessionLocal
            from sqlalchemy import text

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT payload FROM train_telemetry_cache
                        WHERE train_no = :train_no
                        AND fetched_at > NOW() - INTERVAL '24 hours'
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
        await self._railradar.aclose()
        await self._railwayapi.aclose()


ntes_client = NTESClient()
