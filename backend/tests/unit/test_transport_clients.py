"""
Unit tests for NTESClient normalizers and RailRadar client helpers.
No network calls — tests pure data-transformation logic only.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ─────────────────────────────────────────────────────────────
#  NTESClient — _normalize_ntes
# ─────────────────────────────────────────────────────────────


def _client():
    from app.services.ntes_client import NTESClient

    c = NTESClient.__new__(NTESClient)
    c._prev_positions = {}
    c._validated = False
    c._field_map = {}
    return c


def test_normalize_ntes_basic():
    c = _client()
    raw = {
        "stationCode": "GZB",
        "delayInMins": "15",
        "trainName": "Shatabdi Express",
        "trainRunningStatus": "RUNNING",
    }
    result = c._normalize_ntes("12002", raw)
    assert result is not None
    assert result["current_station"] == "GZB"
    assert result["current_delay"] == 15
    assert result["train_name"] == "Shatabdi Express"
    assert result["status"] == "RUNNING"
    assert result["source"] == "NTES"
    assert result["data_quality"] == 0.9


def test_normalize_ntes_wrapped_list():
    """NTES sometimes wraps data in trainLiveStatusList."""
    c = _client()
    raw = {
        "trainLiveStatusList": [
            {"stationCode": "NDLS", "delayInMins": 0, "trainRunningStatus": "ON TIME"}
        ]
    }
    result = c._normalize_ntes("12001", raw)
    assert result is not None
    assert result["current_station"] == "NDLS"
    assert result["current_delay"] == 0
    assert result["status"] == "RUNNING"


def test_normalize_ntes_missing_station_returns_none():
    c = _client()
    raw = {"trainName": "SomeExpress", "delayInMins": 5}
    result = c._normalize_ntes("12002", raw)
    assert result is None


def test_normalize_ntes_bad_delay_defaults_zero():
    c = _client()
    raw = {"stationCode": "CNB", "delayInMins": "not-a-number"}
    result = c._normalize_ntes("12003", raw)
    assert result is not None
    assert result["current_delay"] == 0


def test_normalize_ntes_empty_body_returns_none():
    c = _client()
    result = c._normalize_ntes("12002", {})
    assert result is None


def test_normalize_ntes_delay_with_min_suffix():
    c = _client()
    raw = {"stationCode": "BPL", "delayInMins": "20min"}
    result = c._normalize_ntes("12004", raw)
    assert result is not None
    assert result["current_delay"] == 20


# ─────────────────────────────────────────────────────────────
#  NTESClient — _normalize_railwayapi
# ─────────────────────────────────────────────────────────────


def test_normalize_railwayapi_basic():
    c = _client()
    raw = {
        "result": {
            "current_station_code": "AGC",
            "delay": 10,
            "train_name": "Rajdhani Express",
            "status": "RUNNING",
        }
    }
    result = c._normalize_railwayapi("12309", raw)
    assert result is not None
    assert result["current_station"] == "AGC"
    assert result["current_delay"] == 10
    assert result["source"] == "RAILWAYAPI"


def test_normalize_railwayapi_no_result_key():
    c = _client()
    raw = {"current_station_code": "NGP", "delay": 5, "status": "On Time"}
    result = c._normalize_railwayapi("12002", raw)
    assert result is not None
    assert result["current_station"] == "NGP"


def test_normalize_railwayapi_non_dict_returns_none():
    c = _client()
    raw = {"result": [1, 2, 3]}  # list, not dict
    result = c._normalize_railwayapi("12002", raw)
    assert result is None


# ─────────────────────────────────────────────────────────────
#  NTESClient — _map_running_status
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("YET TO START", "SCHEDULED"),
        ("NOT STARTED", "SCHEDULED"),
        ("RUNNING", "RUNNING"),
        ("ON TIME", "RUNNING"),
        ("ARRIVED", "ARRIVED"),
        ("AT STATION", "ARRIVED"),
        ("DEPARTED", "RUNNING"),
        ("LEFT", "RUNNING"),
        ("REACHED DESTINATION", "COMPLETED"),
        ("TERMINATED", "COMPLETED"),
        ("UNKNOWN_STATUS", "RUNNING"),  # safe default
        ("", "RUNNING"),
    ],
)
def test_map_running_status(raw, expected):
    c = _client()
    assert c._map_running_status(raw) == expected


# ─────────────────────────────────────────────────────────────
#  RailRadar — _map_status helper
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("at-station", "ARRIVED"),
        ("AT STATION", "ARRIVED"),
        ("running", "RUNNING"),
        ("not-started", "SCHEDULED"),
        ("NOT STARTED", "SCHEDULED"),
        ("YET TO START", "SCHEDULED"),
        ("completed", "COMPLETED"),
        ("terminated", "COMPLETED"),
        ("departed", "RUNNING"),
        ("SOMETHING_ELSE", "RUNNING"),
    ],
)
def test_railradar_map_status(raw, expected):
    from app.services.railradar_client import _map_status

    assert _map_status(raw) == expected


# ─────────────────────────────────────────────────────────────
#  RailRadar — normalize_live
# ─────────────────────────────────────────────────────────────


def test_railradar_normalize_live_full():
    from app.services.railradar_client import RailRadarClient

    client = RailRadarClient.__new__(RailRadarClient)
    data = {
        "trainNumber": "12002",
        "trainName": "Rani Kamalapati Shatabdi",
        "status": "running",
        "isLive": True,
        "trackingMode": "real-time",
        "delayMinutes": 5,
        "currentLocation": {"stationCode": "BPL", "status": "at-station"},
        "nextHalt": {"stationCode": "AGC", "stationName": "AGRA CANTT"},
        "train": {"name": "Rani Kamalapati Shatabdi Express"},
    }
    result = client.normalize_live("12002", data)
    assert result["train_no"] == "12002"
    assert result["current_station"] == "BPL"
    assert result["current_delay"] == 5
    assert result["status"] == "ARRIVED"
    assert result["is_live"] is True
    assert result["next_halt"] == "AGC"
    assert result["tracking_mode"] == "real-time"
    assert result["source"] == "RAILRADAR"
    assert result["data_quality"] == 0.95


def test_railradar_normalize_live_no_location():
    from app.services.railradar_client import RailRadarClient

    client = RailRadarClient.__new__(RailRadarClient)
    data = {
        "delayMinutes": 0,
        "status": "not-started",
        "isLive": False,
        "train": {"name": "Some Train"},
    }
    result = client.normalize_live("12001", data)
    assert result["current_station"] == "UNKNOWN"
    assert result["status"] == "SCHEDULED"
    assert result["is_live"] is False


def test_railradar_normalize_live_negative_delay_clamped():
    from app.services.railradar_client import RailRadarClient

    client = RailRadarClient.__new__(RailRadarClient)
    data = {"delayMinutes": -10, "currentLocation": {"stationCode": "NDLS"}}
    result = client.normalize_live("12002", data)
    assert result["current_delay"] == 0


# ─────────────────────────────────────────────────────────────
#  RailRadar — _request helper (mocked httpx)
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_railradar_request_success():
    from app.services.railradar_client import _request

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"success": True, "data": {"foo": "bar"}}

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_resp)

    result = await _request(mock_client, "GET", "/trains/12002/live")
    assert result == {"foo": "bar"}


@pytest.mark.asyncio
async def test_railradar_request_success_false():
    from app.services.railradar_client import _request

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"success": False, "error": "not found"}

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_resp)

    result = await _request(mock_client, "GET", "/trains/99999/live")
    assert result is None


@pytest.mark.asyncio
async def test_railradar_request_404():
    from app.services.railradar_client import _request

    mock_resp = MagicMock()
    mock_resp.status_code = 404

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_resp)

    result = await _request(mock_client, "GET", "/trains/00000/live")
    assert result is None


@pytest.mark.asyncio
async def test_railradar_request_quota_exhausted():
    """All 3 retry attempts hit 429 — should return None without raising."""
    from app.services.railradar_client import _request
    import httpx

    mock_resp = MagicMock()
    mock_resp.status_code = 429

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_resp)

    with patch("app.services.railradar_client.asyncio.sleep", new_callable=AsyncMock):
        result = await _request(mock_client, "GET", "/trains/12002/live")
    assert result is None


@pytest.mark.asyncio
async def test_railradar_request_network_error_retries():
    """ConnectError on all attempts — should return None without raising."""
    import httpx
    from app.services.railradar_client import _request

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(side_effect=httpx.ConnectError("refused"))

    with patch("app.services.railradar_client.asyncio.sleep", new_callable=AsyncMock):
        result = await _request(mock_client, "GET", "/trains/12002/live")
    assert result is None


# ─────────────────────────────────────────────────────────────
#  NTESClient — _fetch_with_retry (via ntes_client module)
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ntes_fetch_with_retry_success():
    from app.services.ntes_client import _fetch_with_retry

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_resp)

    result = await _fetch_with_retry(mock_client, "GET", "/getNTESTrainLiveStatus")
    assert result is mock_resp


@pytest.mark.asyncio
async def test_ntes_fetch_with_retry_429_exhausted():
    from app.services.ntes_client import _fetch_with_retry

    mock_resp = MagicMock()
    mock_resp.status_code = 429

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_resp)

    with patch("app.services.ntes_client.asyncio.sleep", new_callable=AsyncMock):
        result = await _fetch_with_retry(mock_client, "GET", "/test")
    assert result is None


@pytest.mark.asyncio
async def test_ntes_fetch_with_retry_timeout_exhausted():
    import httpx
    from app.services.ntes_client import _fetch_with_retry

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

    with patch("app.services.ntes_client.asyncio.sleep", new_callable=AsyncMock):
        result = await _fetch_with_retry(mock_client, "GET", "/test")
    assert result is None


# ─────────────────────────────────────────────────────────────
#  NTESClient — get_live_status fallback to stale cache
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ntes_get_live_status_returns_stale_cache_when_all_fail():
    """When NTES + RailRadar + RailwayAPI all fail, DB cache is returned with stale flag."""
    from app.services.ntes_client import NTESClient

    client = NTESClient.__new__(NTESClient)
    client._validated = False
    client._field_map = {}

    cached = {"train_no": "12002", "current_station": "GZB", "current_delay": 10}

    client._ntes_live_status = AsyncMock(return_value=None)
    client._railwayapi_live_status = AsyncMock(return_value=None)
    client._railradar_live_status = AsyncMock(return_value=None)
    client._db_cache_fetch = AsyncMock(return_value=cached)

    with patch("app.services.ntes_client.settings") as mock_settings:
        mock_settings.RAILRADAR_API_KEY = ""
        mock_settings.RAILWAYAPI_KEY = ""
        result = await client.get_live_status("12002")

    assert result is not None
    assert result["source"] == "CACHE"
    assert result["stale"] is True
    assert result["data_quality"] == 0.5
    assert "cache_notice" in result


@pytest.mark.asyncio
async def test_ntes_get_live_status_returns_none_when_cache_empty():
    from app.services.ntes_client import NTESClient

    client = NTESClient.__new__(NTESClient)
    client._validated = False
    client._field_map = {}
    client._ntes_live_status = AsyncMock(return_value=None)
    client._railwayapi_live_status = AsyncMock(return_value=None)
    client._railradar_live_status = AsyncMock(return_value=None)
    client._db_cache_fetch = AsyncMock(return_value=None)

    with patch("app.services.ntes_client.settings") as mock_settings:
        mock_settings.RAILRADAR_API_KEY = ""
        mock_settings.RAILWAYAPI_KEY = ""
        result = await client.get_live_status("12002")

    assert result is None


@pytest.mark.asyncio
async def test_ntes_get_live_status_uses_railradar_when_key_set():
    """RailRadar source is tried when key is configured."""
    from app.services.ntes_client import NTESClient

    client = NTESClient.__new__(NTESClient)
    client._validated = False
    client._field_map = {}

    rr_result = {
        "train_no": "12002",
        "current_station": "NDLS",
        "current_delay": 0,
        "source": "RAILRADAR",
        "data_quality": 0.95,
    }

    client._ntes_live_status = AsyncMock(return_value=None)
    client._railradar_live_status = AsyncMock(return_value=rr_result)
    client._cache_to_db = AsyncMock()

    with patch("app.services.ntes_client.settings") as mock_settings:
        mock_settings.RAILRADAR_API_KEY = "rg_test_key"
        mock_settings.RAILWAYAPI_KEY = ""
        result = await client.get_live_status("12002")

    assert result["source"] == "RAILRADAR"
    client._cache_to_db.assert_awaited_once_with("12002", rr_result, source="RAILRADAR")
