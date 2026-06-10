"""
Integration tests for RailMind API.
Uses httpx.AsyncClient with the full ASGI app.

DB-dependent tests (login, audit, scenario-reset) skip gracefully when
PostgreSQL is not available (e.g. running locally without docker-compose).
All rerouting, health, and scenario-read tests work without Postgres.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


def _postgres_down(resp) -> bool:
    """Return True if the 500 is caused by no Postgres."""
    return resp.status_code == 500 and "Connect call failed" in resp.text


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def client():
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Health — no Postgres needed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_root(client):
    r = await client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "RailMind"
    assert "rac_model_loaded" in body


@pytest.mark.asyncio
async def test_health_check(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_agents_health(client):
    r = await client.get("/health/agents")
    assert r.status_code == 200
    agents = r.json()
    assert "MonitorAgent" in agents
    assert "DispatchAgent" in agents
    for name, info in agents.items():
        assert info["status"] == "healthy", f"{name} not healthy"


# ---------------------------------------------------------------------------
# Auth — needs Postgres
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(client):
    try:
        r = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
    except Exception:
        pytest.skip("PostgreSQL not available")
    if _postgres_down(r):
        pytest.skip("PostgreSQL not available")
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    try:
        r = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
    except Exception:
        pytest.skip("PostgreSQL not available")
    if _postgres_down(r):
        pytest.skip("PostgreSQL not available")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Scenario / Cascade — scenario state reads work without Postgres
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scenario_state(client):
    r = await client.get("/api/v1/cascade/scenario")
    assert r.status_code == 200
    body = r.json()
    assert "step" in body
    assert "trains" in body
    assert isinstance(body["trains"], list)


@pytest.mark.asyncio
async def test_scenario_reset_and_step(client):
    try:
        reset = await client.post("/api/v1/cascade/scenario/reset")
    except Exception:
        pytest.skip("PostgreSQL not available")
    if _postgres_down(reset):
        pytest.skip("PostgreSQL not available")
    assert reset.status_code == 200
    assert reset.json()["step"] == 0

    step = await client.post("/api/v1/cascade/scenario/next")
    assert step.status_code == 200
    assert step.json()["step"] == 1


# ---------------------------------------------------------------------------
# Recommendations — in-memory, no Postgres
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_active_recommendations(client):
    r = await client.get("/api/v1/recommendations/active")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_approve_recommendation(client):
    r = await client.get("/api/v1/recommendations/active")
    recs = r.json()
    if not recs:
        pytest.skip("No active recommendations to approve")
    rec_id = recs[0]["id"]
    r2 = await client.post(f"/api/v1/recommendations/{rec_id}/approve")
    assert r2.status_code == 200
    assert r2.json()["is_approved"] is True


# ---------------------------------------------------------------------------
# Rerouting — pure NetworkX, no Postgres
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rerouting_suggest_ndls_cnb(client):
    r = await client.post(
        "/api/v1/rerouting/suggest",
        json={"from_station": "NDLS", "to_station": "CNB"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["passenger_origin"] == "NDLS"
    assert body["passenger_destination"] == "CNB"
    assert isinstance(body["alternatives"], list)
    assert 0.0 < body["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_rerouting_suggest_avoid_section(client):
    r = await client.post(
        "/api/v1/rerouting/suggest",
        json={
            "from_station": "NDLS",
            "to_station": "CNB",
            "avoid_sections": ["NDLS-GZB"],
        },
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_rerouting_suggest_unknown_station(client):
    r = await client.post(
        "/api/v1/rerouting/suggest",
        json={"from_station": "XXXX", "to_station": "CNB"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_rerouting_network_state(client):
    r = await client.get("/api/v1/rerouting/network-state")
    assert r.status_code == 200
    body = r.json()
    assert "nodes" in body
    assert "edges" in body


# ---------------------------------------------------------------------------
# RAC Predictor — in-memory XGBoost, no Postgres
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rac_predict(client):
    r = await client.post(
        "/api/v1/rac/predict",
        json={
            "train_no": "12002",
            "from_station": "NDLS",
            "to_station": "CNB",
            "date": "2026-07-15",
            "current_waitlist_position": 8,
            "current_rac_count": 22,
            "days_to_journey": 10,
            "quota": "GN",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "confirmation_probability" in body
    assert 0.0 <= body["confirmation_probability"] <= 1.0


# ---------------------------------------------------------------------------
# Audit — needs Postgres to persist, but listing may work
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_ledger(client):
    try:
        r = await client.get("/api/v1/audit")
    except Exception:
        pytest.skip("PostgreSQL not available")
    if _postgres_down(r):
        pytest.skip("PostgreSQL not available")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_audit_verify(client):
    try:
        r = await client.get("/api/v1/audit/verify")
    except Exception:
        pytest.skip("PostgreSQL not available")
    if _postgres_down(r):
        pytest.skip("PostgreSQL not available")
    assert r.status_code == 200
    body = r.json()
    assert "chain_valid" in body
