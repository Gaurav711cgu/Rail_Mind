import pytest
from unittest.mock import AsyncMock, patch
from app.services.live_rail_data import (
    LiveRailDataService,
    _first_present,
    _walk_dicts,
    _extract_delay,
    _station_code_from_text,
)


def test_helpers():
    # Test _first_present
    assert _first_present({"a": "val1", "b": ""}, ["b", "a"]) == "val1"
    assert _first_present({"a": None}, ["a"]) is None

    # Test _walk_dicts
    nested = {"a": {"b": 2}, "c": [3, {"d": 4}]}
    dicts = _walk_dicts(nested)
    assert len(dicts) == 3
    assert {"b": 2} in dicts
    assert {"d": 4} in dicts

    # Test _extract_delay
    assert _extract_delay(None) == 0
    assert _extract_delay(15.5) == 15
    assert _extract_delay(-5) == 0
    assert _extract_delay("Late by 20 mins") == 20
    assert _extract_delay("ontime") == 0

    # Test _station_code_from_text
    assert _station_code_from_text("Train is arriving at NDLS station") == "NDLS"
    assert _station_code_from_text("Arriving XYZ") == "XYZ"
    assert _station_code_from_text("") is None


@pytest.mark.asyncio
async def test_live_rail_data_service():
    service = LiveRailDataService()

    # Test watchlist
    assert isinstance(service.watchlist(), list)

    # Test api wrappers
    with patch(
        "app.services.rapidapi_irctc.rapidapi_irctc.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = {"status": "success"}

        res = await service.search_station("NDLS")
        assert res == {"status": "success"}
        mock_get.assert_called_with("/api/v1/searchStation", {"query": "NDLS"})

        await service.search_train("12002")
        mock_get.assert_called_with("/api/v1/searchTrain", {"query": "12002"})

        await service.live_status("12002")
        mock_get.assert_called_with("/api/v1/liveTrainStatus", {"trainNo": "12002", "startDay": 0})

        await service.train_schedule("12002")
        mock_get.assert_called_with("/api/v1/getTrainSchedule", {"trainNo": "12002"})


def test_normalize_train_status():
    service = LiveRailDataService()
    payload = {
        "data": {
            "trainNumber": "12002",
            "trainName": "Shatabdi Exp",
            "currentStationCode": "NDLS",
            "delay": "15 minutes late",
            "status": "Running",
        }
    }
    norm = service.normalize_train_status("12002", payload)
    assert norm["train_no"] == "12002"
    assert norm["train_name"] == "Shatabdi Exp"
    assert norm["current_station"] == "NDLS"
    assert norm["current_delay"] == 15
    assert norm["status"] == "RUNNING"
    assert norm["latitude"] == 28.643
    assert norm["longitude"] == 77.222

    # Fallback paths
    empty_payload = {}
    norm_empty = service.normalize_train_status(
        "12002",
        empty_payload,
        fallback={"train_name": "Fallback Name", "current_station": "GZB", "latitude": 10.0},
    )
    assert norm_empty["train_name"] == "Fallback Name"
    assert norm_empty["current_station"] == "GZB"


@pytest.mark.asyncio
async def test_live_watchlist_snapshot():
    service = LiveRailDataService()

    with patch(
        "app.services.rapidapi_irctc.rapidapi_irctc.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = {
            "data": {
                "trainNumber": "12002",
                "currentStationCode": "NDLS",
                "delay": 0,
            }
        }
        res = await service.live_watchlist_snapshot(
            fallback_trains=[{"train_no": "12002", "train_name": "Shatabdi"}]
        )
        assert len(res) >= 1
        assert res[0]["train_no"] == "12002"


@pytest.mark.asyncio
async def test_live_watchlist_snapshot_failure():
    service = LiveRailDataService()

    # Force mock get to raise exception
    with patch(
        "app.services.rapidapi_irctc.rapidapi_irctc.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.side_effect = Exception("API offline")

        # Should fall back to scenario train and label it STALE
        res = await service.live_watchlist_snapshot(
            fallback_trains=[{"train_no": "12002", "train_name": "Shatabdi", "status": "RUNNING"}]
        )
        assert len(res) >= 1
        assert res[0]["train_no"] == "12002"
        assert "STALE" in res[0]["status"]
        assert res[0]["data_quality"] == 0.25


@pytest.mark.asyncio
async def test_hydrate_scenario_state():
    service = LiveRailDataService()
    state = {"trains": [{"train_no": "12002", "train_name": "Shatabdi"}]}

    # Scenario mode is True, should bypass
    with (
        patch("app.config.settings.SCENARIO_MODE", True),
        patch("app.config.settings.REAL_DATA_REQUIRED", False),
        patch("app.config.settings.RAPIDAPI_IRCTC_KEY", None),
    ):
        res = await service.hydrate_scenario_state(state)
        assert res == state

    # With SCENARIO_MODE = False, should hydrate using live_watchlist_snapshot
    with (
        patch("app.config.settings.SCENARIO_MODE", False),
        patch(
            "app.services.live_rail_data.LiveRailDataService.live_watchlist_snapshot",
            new_callable=AsyncMock,
        ) as mock_snap,
    ):
        mock_snap.return_value = [{"train_no": "12002", "hydrated": True}]
        res = await service.hydrate_scenario_state(state)
        assert res["trains"][0]["hydrated"] is True
        assert res["telemetry_mode"] == "live-rapidapi"
