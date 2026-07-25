import pytest
import pytest_asyncio
from pathlib import Path
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.db.database import (
    get_db,
    Base,
    DBDisruption,
    DBRecommendation,
    DBStation,
    DBSection,
    DBUser,
    DBAuditEntry,
)
from app.config import settings

TEST_UNIT_DB_URL = "sqlite+aiosqlite:///./test_api_unit.db"
engine = create_async_engine(TEST_UNIT_DB_URL, echo=False)
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

    db_path = Path("./test_api_unit.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass


@pytest_asyncio.fixture
async def unit_session():
    async with SessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def unit_client(unit_session):
    async def override_get_db():
        yield unit_session

    app.dependency_overrides[get_db] = override_get_db

    original_rbac = settings.ENFORCE_RBAC
    settings.ENFORCE_RBAC = False

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    settings.ENFORCE_RBAC = original_rbac


# ─────────────────────────────────────────────────────────────
#  Auth Tests
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auth_endpoints_unit(unit_client, unit_session):
    # Test Register
    reg_payload = {"username": "admin_unit", "password": "securepassword"}
    resp = await unit_client.post("/api/v1/auth/register", json=reg_payload)
    assert resp.status_code == 200
    user_data = resp.json()
    assert user_data["username"] == "admin_unit"

    # Test Register Duplicate
    resp_dup = await unit_client.post("/api/v1/auth/register", json=reg_payload)
    assert resp_dup.status_code == 400

    # Test Login Success
    login_payload = {"username": "admin_unit", "password": "securepassword"}
    resp_login = await unit_client.post("/api/v1/auth/login", json=login_payload)
    assert resp_login.status_code == 200
    tokens = resp_login.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # Test Login Fail
    bad_login = {"username": "admin_unit", "password": "wrongpassword"}
    resp_bad = await unit_client.post("/api/v1/auth/login", json=bad_login)
    assert resp_bad.status_code == 401

    # Test GET /me with auth header
    # First set ENFORCE_RBAC to True to test auth logic
    settings.ENFORCE_RBAC = True
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    resp_me = await unit_client.get("/api/v1/auth/me", headers=headers)
    assert resp_me.status_code == 200
    assert resp_me.json()["username"] == "admin_unit"

    # Test GET /me unauthenticated
    resp_me_unauth = await unit_client.get("/api/v1/auth/me")
    assert resp_me_unauth.status_code == 401
    settings.ENFORCE_RBAC = False

    # Test Operator Performance
    resp_perf = await unit_client.get("/api/v1/auth/operator-performance")
    assert resp_perf.status_code == 200
    assert "variance_score" in resp_perf.json()

    # Test Refresh Token
    refresh_payload = {"refresh_token": tokens["refresh_token"]}
    resp_refresh = await unit_client.post("/api/v1/auth/refresh", json=refresh_payload)
    assert resp_refresh.status_code == 200
    assert "access_token" in resp_refresh.json()

    # Test Bad Refresh Token
    bad_refresh = {"refresh_token": "invalid_token"}
    resp_bad_refresh = await unit_client.post("/api/v1/auth/refresh", json=bad_refresh)
    assert resp_bad_refresh.status_code == 401

    # Test Logout (requires active user session)
    settings.ENFORCE_RBAC = True
    resp_logout = await unit_client.post("/api/v1/auth/logout", headers=headers)
    assert resp_logout.status_code == 200
    settings.ENFORCE_RBAC = False


# ─────────────────────────────────────────────────────────────
#  Cascade Tests
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cascade_scenario_endpoints(unit_client, unit_session):
    # Scenario State
    resp = await unit_client.get("/api/v1/cascade/scenario")
    assert resp.status_code == 200

    # Corridor Metrics
    resp_metrics = await unit_client.get("/api/v1/cascade/corridor-metrics")
    assert resp_metrics.status_code == 200

    # Weather endpoints
    resp_weather = await unit_client.get("/api/v1/cascade/weather")
    assert resp_weather.status_code == 200
    assert resp_weather.json()["visibility_meters"] == 2200

    resp_weather_post = await unit_client.post(
        "/api/v1/cascade/weather?visibility=400&fog_density=35&speed_limit=60"
    )
    assert resp_weather_post.status_code == 200
    assert resp_weather_post.json()["active_warning"] == "SEVERE_FOG_WARNING"

    # Kavach toggle
    resp_kavach = await unit_client.post(
        "/api/v1/cascade/kavach-toggle?section_code=DLI-GZB&active=false"
    )
    assert resp_kavach.status_code == 200
    assert resp_kavach.json()["active"] is False

    resp_kavach_bad = await unit_client.post(
        "/api/v1/cascade/kavach-toggle?section_code=INVALID&active=false"
    )
    assert resp_kavach_bad.status_code == 404

    # Disruption details
    resp_disp_det = await unit_client.get(
        "/api/v1/cascade/disruption-details?disruption_id=nonexistent"
    )
    assert resp_disp_det.status_code == 200
    assert (
        "Clearance" in resp_disp_det.json().get("details", "")
        or "nominal" in resp_disp_det.json().get("details", "").lower()
        or "active disruptions" in resp_disp_det.json().get("details", "").lower()
    )

    # Demo run
    resp_demo = await unit_client.post("/api/v1/cascade/scenario/demo-run")
    assert resp_demo.status_code == 200
    assert resp_demo.json()["status"] == "demo_complete"

    # Impact Summary
    resp_impact = await unit_client.get("/api/v1/cascade/impact-summary")
    assert resp_impact.status_code == 200

    # Simulate GET (Scenario context)
    # Put a mock disruption in scenario first
    from app.core.scenario_engine import scenario_engine

    scenario_engine.current_step = 1
    state = scenario_engine.get_state()
    disp_id = state["disruptions"][0]["id"]

    resp_sim_get = await unit_client.get(f"/api/v1/cascade/simulate?disruption_id={disp_id}")
    assert (
        resp_sim_get.shape_code
        if hasattr(resp_sim_get, "shape_code")
        else resp_sim_get.status_code == 200
    )
    assert resp_sim_get.json()["root_disruption_id"] == disp_id

    # Simulate GET Not Found
    resp_sim_get_bad = await unit_client.get("/api/v1/cascade/simulate?disruption_id=invalid")
    assert resp_sim_get_bad.status_code == 404


@pytest.mark.asyncio
async def test_recommendations_approve_override_scenario_and_db(unit_client, unit_session):
    # 1. SCENARIO MODE = True
    # Seed scenario engine state
    from app.core.scenario_engine import scenario_engine

    scenario_engine.current_step = 4
    state = scenario_engine.get_state()
    rec_id = state["recommendations"][0]["id"]

    # Test Approve Recommendation
    resp = await unit_client.post(f"/api/v1/cascade/recommendations/{rec_id}/approve")
    assert resp.status_code == 200
    assert resp.json()["is_approved"] is True

    # Test Override Recommendation
    resp_over = await unit_client.post(
        f"/api/v1/cascade/recommendations/{rec_id}/override?override_reason=SafetyOverride"
    )
    assert resp_over.status_code == 200
    assert resp_over.json()["is_approved"] is False
    assert resp_over.json()["override_reason"] == "SafetyOverride"

    # Approve Nonexistent
    resp_bad = await unit_client.post("/api/v1/cascade/recommendations/nonexistent/approve")
    assert resp_bad.status_code == 404

    # Override Nonexistent
    resp_over_bad = await unit_client.post(
        "/api/v1/cascade/recommendations/nonexistent/override?override_reason=Bypass"
    )
    assert resp_over_bad.status_code == 404

    # 2. SCENARIO MODE = False
    original_mode = settings.SCENARIO_MODE
    settings.SCENARIO_MODE = False
    try:
        # Seed DB Recommendation
        db_rec = DBRecommendation(
            id="rec-db-test",
            disruption_id="disp-001",
            type="HOLD",
            target_train="12002",
            target_section="GZB-ALJN",
            reasoning="Reasoning text",
            confidence=0.85,
            tier=1,
            is_approved=False,
            generated_at=datetime.utcnow(),
        )
        unit_session.add(db_rec)
        await unit_session.commit()

        # Approve DB
        resp_db = await unit_client.post("/api/v1/cascade/recommendations/rec-db-test/approve")
        assert resp_db.status_code == 200
        assert resp_db.json()["is_approved"] is True

        # Override DB
        resp_db_over = await unit_client.post(
            "/api/v1/cascade/recommendations/rec-db-test/override?override_reason=OverrideDBText"
        )
        assert resp_db_over.status_code == 200
        assert resp_db_over.json()["is_approved"] is False
        assert resp_db_over.json()["override_reason"] == "OverrideDBText"

        # Nonexistent DB
        resp_db_bad = await unit_client.post(
            "/api/v1/cascade/recommendations/rec-db-nonexistent/approve"
        )
        assert resp_db_bad.status_code == 404

        resp_db_over_bad = await unit_client.post(
            "/api/v1/cascade/recommendations/rec-db-nonexistent/override?override_reason=Bypass"
        )
        assert resp_db_over_bad.status_code == 404

        # Simulate GET in DB mode (returns 501)
        resp_sim_db = await unit_client.get("/api/v1/cascade/simulate?disruption_id=any")
        assert resp_sim_db.status_code == 501
    finally:
        settings.SCENARIO_MODE = original_mode


# ─────────────────────────────────────────────────────────────
#  Disruptions Tests (DB Mode)
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_disruptions_db_mode_unit(unit_client, unit_session):
    original_mode = settings.SCENARIO_MODE
    settings.SCENARIO_MODE = False
    try:
        # Seed Disruption
        db_disp = DBDisruption(
            id="disp-unit-db-001",
            train_no="12002",
            section_from="NDLS",
            section_to="GZB",
            disruption_type="SIGNAL_FAILURE",
            severity="HIGH",
            cascade_depth=1,
            trains_affected_json="[]",
            passengers_affected=150,
            status="ACTIVE",
            detected_at=datetime.utcnow(),
        )
        unit_session.add(db_disp)
        await unit_session.commit()

        # List Disruptions
        resp = await unit_client.get("/api/v1/disruptions")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
        assert any(d["id"] == "disp-unit-db-001" for d in resp.json())

        # Get Disruption
        resp_get = await unit_client.get("/api/v1/disruptions/disp-unit-db-001")
        assert resp_get.status_code == 200
        assert resp_get.json()["id"] == "disp-unit-db-001"

        # Create Disruption
        payload = {
            "id": "disp-unit-db-created",
            "train_no": "22415",
            "section_from": "GZB",
            "section_to": "ALJN",
            "disruption_type": "WEATHER",
            "severity": "MEDIUM",
            "cascade_depth": 0,
            "trains_affected": [],
            "passengers_affected": 200,
            "status": "ACTIVE",
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }
        resp_create = await unit_client.post("/api/v1/disruptions", json=payload)
        assert resp_create.status_code == 200
        assert resp_create.json()["id"] == "disp-unit-db-created"
    finally:
        settings.SCENARIO_MODE = original_mode


# ─────────────────────────────────────────────────────────────
#  RAC / Recommendations / Rerouting / Stream / Health Tests
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rac_extended_routes(unit_client):
    # Historical trends
    resp = await unit_client.get("/api/v1/rac/historical-trends?train_no=12002")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # Model health
    resp_health = await unit_client.get("/api/v1/rac/model-health")
    assert resp_health.status_code == 200
    assert "model_loaded" in resp_health.json()

    # Drift report
    resp_drift = await unit_client.get("/api/v1/rac/drift-report")
    assert resp_drift.status_code == 200
    assert "dataset_drift" in resp_drift.json()
    assert "drift_by_columns" in resp_drift.json()



@pytest.mark.asyncio
async def test_recommendations_escalated_routes(unit_client):
    # List all
    resp = await unit_client.get("/api/v1/recommendations")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # List active
    resp_act = await unit_client.get("/api/v1/recommendations/active")
    assert resp_act.status_code == 200

    # Approve
    resp_app = await unit_client.post("/api/v1/recommendations/rec-hold-001/approve")
    assert resp_app.status_code == 200
    assert resp_app.json()["is_approved"] is True

    # Override
    resp_over = await unit_client.post(
        "/api/v1/recommendations/rec-hold-001/override", json={"reason": "SafetyFirst"}
    )
    assert resp_over.status_code == 200
    assert resp_over.json()["override_reason"] == "SafetyFirst"

    # Approve Bad
    resp_app_bad = await unit_client.post("/api/v1/recommendations/rec-hold-nonexistent/approve")
    assert resp_app_bad.status_code == 404

    # Override Bad
    resp_over_bad = await unit_client.post(
        "/api/v1/recommendations/rec-hold-nonexistent/override", json={"reason": "Bypass"}
    )
    assert resp_over_bad.status_code == 404


@pytest.mark.asyncio
async def test_rerouting_extended_routes_scenario_and_db(unit_client, unit_session):
    # 1. SCENARIO MODE = True
    resp = await unit_client.get("/api/v1/rerouting")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp_single = await unit_client.get("/api/v1/rerouting/disp-001")
    assert resp_single.status_code == 200

    resp_single_bad = await unit_client.get("/api/v1/rerouting/nonexistent")
    assert resp_single_bad.status_code == 200  # scenario fallback matches suggestions

    # 2. SCENARIO MODE = False
    original_mode = settings.SCENARIO_MODE
    settings.SCENARIO_MODE = False
    try:
        # Seed Stations and Sections
        st1 = DBStation(code="NDLS", name="New Delhi", zone="NR")
        st2 = DBStation(code="GZB", name="Ghaziabad", zone="NR")
        sec1 = DBSection(
            id=1, from_station="NDLS", to_station="GZB", distance_km=25.0, max_speed_kmh=110
        )
        unit_session.add_all([st1, st2, sec1])
        await unit_session.commit()

        # Network State
        resp_net = await unit_client.get("/api/v1/rerouting/network-state")
        assert resp_net.status_code == 200
        assert len(resp_net.json()["nodes"]) >= 2

        # Rerouting suggestions in DB mode
        resp_list = await unit_client.get("/api/v1/rerouting")
        assert resp_list.status_code == 200
        assert len(resp_list.json()) == 0

        # suggest reroute
        payload = {"from_station": "NDLS", "to_station": "GZB", "train_no": "12002"}
        resp_sug = await unit_client.post("/api/v1/rerouting/suggest", json=payload)
        assert resp_sug.status_code == 200
        assert "NDLS" in resp_sug.json()["advisory_text"]
    finally:
        settings.SCENARIO_MODE = original_mode


@pytest.mark.asyncio
async def test_stream_sse_endpoints(unit_client):
    from unittest.mock import patch

    # Mock the infinite event generators to yield once and exit cleanly, preventing event loop hanging/timeouts
    async def mock_agent_event_generator():
        yield "data: {}\n\n"

    async def mock_position_event_generator():
        yield "data: {}\n\n"

    with (
        patch("app.api.v1.routes.stream._agent_event_generator", mock_agent_event_generator),
        patch("app.api.v1.routes.stream._position_event_generator", mock_position_event_generator),
    ):
        # Test SSE route `/positions`
        async with unit_client.stream("GET", "/api/v1/stream/positions") as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line.strip():
                    assert "data:" in line
                    break

        # Test SSE route `/agents`
        async with unit_client.stream("GET", "/api/v1/stream/agents") as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line.strip():
                    assert "data:" in line
                    break


@pytest.mark.asyncio
async def test_trains_endpoints_extended(unit_client, unit_session):
    # 1. SCENARIO MODE = True
    resp_list = await unit_client.get("/api/v1/trains")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) > 0

    resp_single = await unit_client.get("/api/v1/trains/12002")
    assert resp_single.status_code == 200
    assert resp_single.json()["train_no"] == "12002"

    resp_bad = await unit_client.get("/api/v1/trains/invalid_train")
    assert resp_bad.status_code == 404

    # Update speed lock
    resp_speed = await unit_client.post(
        "/api/v1/trains/speed-lock?section_code=DLI-GZB&speed_limit=60"
    )
    assert resp_speed.status_code == 200
    assert resp_speed.json()["speed_limit"] == 60

    resp_speed_bad = await unit_client.post(
        "/api/v1/trains/speed-lock?section_code=INVALID&speed_limit=60"
    )
    assert resp_speed_bad.status_code == 404

    # Search & Schedule
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.services.rapidapi_irctc.rapidapi_irctc.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = {"status": "success", "data": {}}

        resp_search = await unit_client.get("/api/v1/trains/rapidapi/search-station?query=NDLS")
        assert resp_search.status_code == 200

        resp_sched = await unit_client.get("/api/v1/trains/rapidapi/train-schedule?train_no=12002")
        assert resp_sched.status_code == 200

    # 2. SCENARIO MODE = False
    original_mode = settings.SCENARIO_MODE
    settings.SCENARIO_MODE = False
    try:
        # DB trains list (empty)
        resp_db_list = await unit_client.get("/api/v1/trains")
        assert resp_db_list.status_code == 200

        # DB train single (not found)
        resp_db_single = await unit_client.get("/api/v1/trains/99999")
        assert resp_db_single.status_code == 404
    finally:
        settings.SCENARIO_MODE = original_mode


@pytest.mark.asyncio
async def test_health_endpoints_unit_route(unit_client):
    resp = await unit_client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    resp_sys = await unit_client.get("/api/v1/health/system")
    assert resp_sys.status_code == 200

    resp_fresh = await unit_client.get("/api/v1/health/data-freshness")
    assert resp_fresh.status_code == 200

    resp_agents = await unit_client.get("/api/v1/health/agents")
    assert resp_agents.status_code == 200


# ─────────────────────────────────────────────────────────────
#  Additional Coverage Tests
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rac_all_endpoints(unit_client):
    # Predict with dummy query
    payload = {
        "train_no": "12002",
        "from_station": "NDLS",
        "to_station": "GZB",
        "date": "2026-06-12",
        "current_waitlist_position": 10,
        "current_rac_count": 5,
        "days_to_journey": 15,
        "quota": "GN",
    }
    resp = await unit_client.post("/api/v1/rac/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "confirmation_probability" in data
    assert "key_factors" in data

    # Alternative suggestions
    resp_alt = await unit_client.get(
        "/api/v1/rac/alternative-suggestions?train_no=12002&from_station=NDLS&to_station=GZB"
    )
    assert resp_alt.status_code == 200
    assert isinstance(resp_alt.json(), list)

    # Quota heatmap
    resp_heat = await unit_client.get("/api/v1/rac/quota-heatmap?train_no=12002&waitlist_pos=10")
    assert resp_heat.status_code == 200
    assert isinstance(resp_heat.json(), list)

    # Model health
    resp_health = await unit_client.get("/api/v1/rac/model-health")
    assert resp_health.status_code == 200
    assert "model_version" in resp_health.json()

    # Train stats
    resp_stats = await unit_client.get("/api/v1/rac/train-stats/12002")
    assert resp_stats.status_code == 200
    assert resp_stats.json()["train_no"] == "12002"

    # Engine error mock
    from unittest.mock import patch

    with patch(
        "app.ml.rac_predictor.rac_predictor.predict", side_effect=Exception("ML engine crash")
    ):
        resp_err = await unit_client.post("/api/v1/rac/predict", json=payload)
        assert resp_err.status_code == 500


@pytest.mark.asyncio
async def test_audit_scenario_and_corrupted_chain(unit_client, unit_session):
    # 1. Test empty DB under scenario mode
    original_mode = settings.SCENARIO_MODE
    settings.SCENARIO_MODE = True
    try:
        # Clear DBAuditEntry first (in case integration test seeded anything)
        from sqlalchemy import delete

        await unit_session.execute(delete(DBAuditEntry))
        await unit_session.commit()

        # Advance scenario step to have some audit entries
        from app.core.scenario_engine import scenario_engine

        scenario_engine.current_step = 1

        # List audit logs (scenario mode fallback)
        resp_list = await unit_client.get("/api/v1/audit")
        assert resp_list.status_code == 200
        assert len(resp_list.json()) > 0

        # Statistics (scenario mode fallback)
        resp_stats = await unit_client.get("/api/v1/audit/statistics")
        assert resp_stats.status_code == 200
        assert resp_stats.json()["total_blocks_sealed"] > 0

        # Verify chain on empty DB
        resp_verify = await unit_client.get("/api/v1/audit/verify")
        assert resp_verify.status_code == 200
        assert resp_verify.json()["chain_valid"] is True
    finally:
        settings.SCENARIO_MODE = original_mode

    # 2. Test calculate_content_hash directly
    from app.api.v1.routes.audit import calculate_content_hash

    test_entry = DBAuditEntry(
        id=1001,
        agent_name="TestAgent",
        action_type="TEST",
        target="None",
        reasoning="Test reason",
        confidence=0.95,
        prev_hash="a" * 64,
        current_hash="b" * 64,
        timestamp=datetime.utcnow(),
    )
    h = calculate_content_hash(test_entry)
    assert isinstance(h, str)

    # 3. Test corrupted chains in DB mode
    settings.SCENARIO_MODE = False
    try:
        # Add corrupted genesis (prev_hash is not zero)
        bad_genesis = DBAuditEntry(
            id=101,
            agent_name="Agent",
            action_type="ACTION",
            target="T",
            reasoning="Reason",
            confidence=0.9,
            prev_hash="1" * 64,
            current_hash="2" * 64,
            timestamp=datetime(2026, 6, 1, 12, 0, 0),
        )
        # Add out-of-order timestamp or link breakage
        bad_link = DBAuditEntry(
            id=102,
            agent_name="Agent",
            action_type="ACTION",
            target="T",
            reasoning="Reason",
            confidence=0.9,
            prev_hash="3" * 64,  # broken link
            current_hash="4" * 64,
            timestamp=datetime(2026, 5, 1, 12, 0, 0),  # out of order timestamp
        )
        unit_session.add_all([bad_genesis, bad_link])
        await unit_session.commit()

        resp_verify = await unit_client.get("/api/v1/audit/verify")
        assert resp_verify.status_code == 200
        verify_data = resp_verify.json()
        assert verify_data["chain_valid"] is False
        assert verify_data["genesis_valid"] is False
        assert verify_data["links_valid"] is False
        assert verify_data["timestamps_valid"] is False
        assert "101" in verify_data["corrupted_records"]
    finally:
        settings.SCENARIO_MODE = original_mode


@pytest.mark.asyncio
async def test_rerouting_edge_cases_and_500(unit_client, unit_session):
    # Test get_routing_for_disruption not found (DB mode empty suggestions)
    original_mode = settings.SCENARIO_MODE
    settings.SCENARIO_MODE = False
    try:
        resp = await unit_client.get("/api/v1/rerouting/disp-nonexistent")
        assert resp.status_code == 404
    finally:
        settings.SCENARIO_MODE = original_mode

    # Test 500 error on rerouting suggest when db error happens
    from unittest.mock import patch

    with patch.object(unit_session, "execute", side_effect=Exception("Database error")):
        payload = {"from_station": "NDLS", "to_station": "GZB", "train_no": "12002"}
        resp_suggest = await unit_client.post("/api/v1/rerouting/suggest", json=payload)
        assert resp_suggest.status_code == 500

        resp_net = await unit_client.get("/api/v1/rerouting/network-state")
        assert resp_net.status_code == 500


@pytest.mark.asyncio
async def test_auth_edge_cases_rbac(unit_client, unit_session):
    from fastapi import HTTPException
    from app.api.v1.routes.auth import (
        verify_password,
        get_password_hash,
        create_access_token,
        create_refresh_token,
    )

    # 1. verify_password exception
    assert verify_password("pass", None) is False

    # 2. get_current_user credentials exception with invalid token
    original_rbac = settings.ENFORCE_RBAC
    settings.ENFORCE_RBAC = True
    try:
        resp = await unit_client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"}
        )
        assert resp.status_code == 401

        # 3. inactive user
        inactive_user = DBUser(
            username="inactive_usr",
            email="inactive@test.com",
            password_hash=get_password_hash("password"),
            role="PASSENGER",
            is_active=False,
        )
        unit_session.add(inactive_user)
        await unit_session.commit()

        token = create_access_token(data={"sub": "inactive_usr", "role": "PASSENGER"})
        resp_inactive = await unit_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp_inactive.status_code == 400
        assert resp_inactive.json()["detail"] == "Inactive user"

        # 4. test role checker logic directly to avoid import-time dependency override issues
        from app.api.v1.routes.auth import require_roles

        role_checker = require_roles("CONTROLLER", "ADMIN")

        class MockRequest:
            def __init__(self, headers):
                self.headers = headers

        # Bypassed when ENFORCE_RBAC is False
        settings.ENFORCE_RBAC = False
        mock_req = MockRequest(headers={})
        assert await role_checker(mock_req, db=unit_session) is None
        settings.ENFORCE_RBAC = True

        # Passenger is forbidden (raises 403)
        passenger_token = create_access_token(data={"sub": "passenger_usr", "role": "PASSENGER"})
        passenger_user = DBUser(
            username="passenger_usr",
            email="passenger@test.com",
            password_hash=get_password_hash("password"),
            role="PASSENGER",
            is_active=True,
        )
        unit_session.add(passenger_user)
        await unit_session.commit()

        mock_req_p = MockRequest(headers={"Authorization": f"Bearer {passenger_token}"})
        with pytest.raises(HTTPException) as exc_info:
            await role_checker(mock_req_p, db=unit_session)
        assert exc_info.value.status_code == 403

        # Controller is allowed
        controller_token = create_access_token(data={"sub": "controller_usr", "role": "CONTROLLER"})
        controller_user = DBUser(
            username="controller_usr",
            email="controller@test.com",
            password_hash=get_password_hash("password"),
            role="CONTROLLER",
            is_active=True,
        )
        unit_session.add(controller_user)
        await unit_session.commit()

        mock_req_c = MockRequest(headers={"Authorization": f"Bearer {controller_token}"})
        res_user = await role_checker(mock_req_c, db=unit_session)
        assert res_user.username == "controller_usr"

        # 5. bad refresh token missing "type": "refresh"
        bad_ref = create_access_token(data={"sub": "passenger_usr"})
        resp_ref_bad = await unit_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": bad_ref}
        )
        assert resp_ref_bad.status_code == 401

        # 6. Inactive user refresh
        inactive_ref = create_refresh_token(data={"sub": "inactive_usr"})
        resp_ref_inactive = await unit_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": inactive_ref}
        )
        assert resp_ref_inactive.status_code == 401
    finally:
        settings.ENFORCE_RBAC = original_rbac
