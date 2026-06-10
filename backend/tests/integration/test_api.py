import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoints(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

    response = await client.get("/api/v1/health/agents")
    assert response.status_code == 200
    data = response.json()
    assert "MonitorAgent" in data
    assert "DispatchAgent" in data

    response = await client.get("/api/v1/health/data-freshness")
    assert response.status_code == 200
    assert "watchlist" in response.json()

    response = await client.get("/api/v1/health/system")
    assert response.status_code == 200
    system_data = response.json()
    assert system_data["status"] in ("operational", "degraded")
    assert "uptime_seconds" in system_data
    assert "performance" in system_data
    assert "components" in system_data
    assert system_data["components"]["database"] == "connected"
    assert "test_coverage" in system_data


@pytest.mark.asyncio
async def test_auth_flow(client: AsyncClient):
    # Register a test user
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={"username": "test_controller", "password": "securepassword123"},
    )
    assert reg_response.status_code == 200
    reg_data = reg_response.json()
    assert reg_data["username"] == "test_controller"

    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "test_controller", "password": "securepassword123"},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    assert login_data["role"] == "PASSENGER"  # default role

    # Refresh token
    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login_data["refresh_token"]}
    )
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert "access_token" in refresh_data
    assert "refresh_token" in refresh_data


@pytest.mark.asyncio
async def test_train_endpoints(client: AsyncClient):
    response = await client.get("/api/v1/trains")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["train_no"] in ["12002", "22415", "BOXN-902"]

    # Get details of train 12002
    response_12002 = await client.get("/api/v1/trains/12002")
    assert response_12002.status_code == 200
    data_12002 = response_12002.json()
    assert data_12002["train_no"] == "12002"
    assert len(data_12002["route"]) > 0


@pytest.mark.asyncio
async def test_recommendations_and_rerouting(client: AsyncClient):
    # List recommendations
    response = await client.get("/api/v1/recommendations")
    assert response.status_code == 200
    recs = response.json()
    assert len(recs) > 0
    rec_id = recs[0]["id"]

    # Approve recommendation
    response_approve = await client.post(f"/api/v1/recommendations/{rec_id}/approve")
    assert response_approve.status_code == 200
    assert response_approve.json()["is_approved"] is True

    # Suggest rerouting path
    response_reroute = await client.post(
        "/api/v1/rerouting/suggest",
        json={"from_station": "NDLS", "to_station": "ALJN", "train_no": "12002"},
    )
    assert response_reroute.status_code == 200
    reroute_data = response_reroute.json()
    assert "suggested path" in reroute_data["advisory_text"].lower()
    assert "bypassed" in reroute_data["advisory_text"].lower()

    # Get network state
    response_net = await client.get("/api/v1/rerouting/network-state")
    assert response_net.status_code == 200
    net_data = response_net.json()
    assert "nodes" in net_data
    assert "edges" in net_data
