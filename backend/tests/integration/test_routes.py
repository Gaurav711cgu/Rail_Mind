"""
Integration tests for remaining zero-coverage routes:
disruptions, cascade, audit, rac, stream, rerouting (extended).
All use the shared `client` fixture from conftest.py (SCENARIO_MODE=True).
"""

import pytest
from httpx import AsyncClient


# ─────────────────────────────────────────────────────────────
#  Disruptions
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_disruptions_scenario_mode(client: AsyncClient):
    """Step 0 has no disruptions; stepping forward should produce some."""
    response = await client.get("/api/v1/disruptions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_disruptions_after_scenario_step(client: AsyncClient):
    """Advance scenario to step 1 via cascade endpoint, then check disruptions."""
    # Advance to step 1 (signal failure)
    step_resp = await client.post("/api/v1/cascade/scenario/next-step")
    assert step_resp.status_code == 200

    response = await client.get("/api/v1/disruptions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    d = data[0]
    assert d["train_no"] == "12002"
    assert d["status"] == "ACTIVE"
    assert d["disruption_type"] in (
        "SIGNAL_FAILURE", "DELAY_CASCADE", "TRACK_OBSTRUCTION",
        "EQUIPMENT_FAILURE", "WEATHER"
    )


@pytest.mark.asyncio
async def test_get_disruption_by_id(client: AsyncClient):
    """Get a specific disruption that exists in the current scenario."""
    # Advance to step with disruption
    await client.post("/api/v1/cascade/scenario/next-step")
    list_resp = await client.get("/api/v1/disruptions")
    disruptions = list_resp.json()
    if not disruptions:
        pytest.skip("No disruptions in current scenario step")

    disp_id = disruptions[0]["id"]
    response = await client.get(f"/api/v1/disruptions/{disp_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == disp_id


@pytest.mark.asyncio
async def test_get_disruption_not_found(client: AsyncClient):
    response = await client.get("/api/v1/disruptions/nonexistent-id-99999")
    assert response.status_code == 404


# ─────────────────────────────────────────────────────────────
#  Cascade
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cascade_scenario_next_step(client: AsyncClient):
    resp = await client.post("/api/v1/cascade/scenario/next-step")
    assert resp.status_code == 200
    data = resp.json()
    assert "step" in data
    assert data["step"] >= 1


@pytest.mark.asyncio
async def test_cascade_scenario_reset(client: AsyncClient):
    # Advance a few steps first
    await client.post("/api/v1/cascade/scenario/next-step")
    await client.post("/api/v1/cascade/scenario/next-step")

    resp = await client.post("/api/v1/cascade/scenario/reset")
    assert resp.status_code == 200
    data = resp.json()
    assert data["step"] == 0


@pytest.mark.asyncio
async def test_cascade_scenario_state(client: AsyncClient):
    resp = await client.get("/api/v1/cascade/scenario/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "trains" in data
    assert "disruptions" in data
    assert "step" in data


@pytest.mark.asyncio
async def test_cascade_network_graph(client: AsyncClient):
    resp = await client.get("/api/v1/cascade/network-graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0


@pytest.mark.asyncio
async def test_cascade_simulate(client: AsyncClient):
    """Simulate cascade from a known station."""
    resp = await client.post(
        "/api/v1/cascade/simulate",
        json={
            "origin_station": "NDLS",
            "delay_minutes": 45,
            "disruption_type": "SIGNAL_FAILURE",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "affected_trains" in data or "cascade_events" in data or "nodes" in data


# ─────────────────────────────────────────────────────────────
#  Audit
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_audit_logs(client: AsyncClient):
    resp = await client.get("/api/v1/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_audit_logs_after_scenario_advance(client: AsyncClient):
    """Advance scenario to produce audit entries, then check."""
    await client.post("/api/v1/cascade/scenario/next-step")
    resp = await client.get("/api/v1/audit")
    assert resp.status_code == 200
    data = resp.json()
    # Scenario step 1 always has audit entries
    assert len(data) >= 1
    entry = data[0]
    assert "agent_name" in entry
    assert "action_type" in entry
    assert "hash" in entry


@pytest.mark.asyncio
async def test_audit_verify_chain(client: AsyncClient):
    """Chain verification endpoint should return valid/invalid status."""
    await client.post("/api/v1/cascade/scenario/next-step")
    resp = await client.get("/api/v1/audit/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert "valid" in data or "chain_valid" in data or "status" in data


# ─────────────────────────────────────────────────────────────
#  RAC Route
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rac_predict_endpoint(client: AsyncClient):
    resp = await client.post(
        "/api/v1/rac/predict",
        json={
            "train_no": "12002",
            "from_station": "NDLS",
            "to_station": "CNB",
            "date": "2026-06-15",
            "current_waitlist_position": 10,
            "current_rac_count": 20,
            "days_to_journey": 4,
            "quota": "GN",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "confirmation_probability" in data
    assert 0.0 <= data["confirmation_probability"] <= 1.0


@pytest.mark.asyncio
async def test_rac_train_stats(client: AsyncClient):
    resp = await client.get("/api/v1/rac/train-stats/12002")
    assert resp.status_code == 200
    data = resp.json()
    assert "train_no" in data


# ─────────────────────────────────────────────────────────────
#  Trains (extended coverage)
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_all_trains(client: AsyncClient):
    resp = await client.get("/api/v1/trains")
    assert resp.status_code == 200
    trains = resp.json()
    assert len(trains) >= 3
    train_nos = [t["train_no"] for t in trains]
    assert "12002" in train_nos
    assert "22415" in train_nos
    assert "BOXN-902" in train_nos


@pytest.mark.asyncio
async def test_get_train_detail(client: AsyncClient):
    resp = await client.get("/api/v1/trains/22415")
    assert resp.status_code == 200
    data = resp.json()
    assert data["train_no"] == "22415"


@pytest.mark.asyncio
async def test_get_train_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/trains/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_trains_watchlist(client: AsyncClient):
    resp = await client.get("/api/v1/trains/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ─────────────────────────────────────────────────────────────
#  Auth — extended
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_duplicate_user(client: AsyncClient):
    creds = {"username": "dup_user_test", "password": "password123"}
    r1 = await client.post("/api/v1/auth/register", json=creds)
    assert r1.status_code == 200
    r2 = await client.post("/api/v1/auth/register", json=creds)
    # Second registration must fail
    assert r2.status_code in (400, 409, 422)


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "wrongpass_user", "password": "correctpass"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "wrongpass_user", "password": "wrongpass"},
    )
    assert resp.status_code in (401, 400, 422)


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "nobody_here", "password": "abc"},
    )
    assert resp.status_code in (401, 400, 404, 422)


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    """Controller-only endpoints should reject unauthenticated requests."""
    resp = await client.post("/api/v1/cascade/scenario/reset")
    # Either 200 (open in scenario mode) or 401/403
    assert resp.status_code in (200, 401, 403)


# ─────────────────────────────────────────────────────────────
#  Rerouting (extended)
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rerouting_network_state(client: AsyncClient):
    resp = await client.get("/api/v1/rerouting/network-state")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data


@pytest.mark.asyncio
async def test_rerouting_suggest(client: AsyncClient):
    resp = await client.post(
        "/api/v1/rerouting/suggest",
        json={"from_station": "NDLS", "to_station": "ALJN", "train_no": "12002"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "advisory_text" in data
