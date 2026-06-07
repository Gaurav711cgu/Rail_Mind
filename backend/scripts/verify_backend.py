import sys
import os
from fastapi.testclient import TestClient

# Append project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

client = TestClient(app)

def run_tests():
    print("====================================================")
    print("      RAILMIND BACKEND INTEGRITY VERIFICATION       ")
    print("====================================================")
    
    # 1. Test Health Check
    print("\n[Test 1] GET /health ... ", end="")
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    print("PASS")

    # 2. Test Root Endpoint
    print("[Test 2] GET / ... ", end="")
    res = client.get("/")
    assert res.status_code == 200
    assert "Welcome" in res.json()["message"]
    print("PASS")

    # 3. Test User Registration & Login
    print("[Test 3] POST /api/v1/auth/register ... ", end="")
    # Use randomized username to avoid duplicates in local db
    import time
    username = f"verify_user_{int(time.time())}"
    res = client.post(
        "/api/v1/auth/register?email=verify@railmind.gov.in&role=CONTROLLER&zone=NR",
        json={"username": username, "password": "securepassword123"}
    )
    assert res.status_code == 200
    assert res.json()["username"] == username
    print("PASS")

    print("[Test 4] POST /api/v1/auth/login ... ", end="")
    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "securepassword123"}
    )
    assert res.status_code == 200
    token_data = res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("PASS")

    print("[Test 5] GET /api/v1/auth/me ... ", end="")
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["username"] == username
    print("PASS")

    # 4. Test Train Tracking Routes
    print("[Test 6] GET /api/v1/trains ... ", end="")
    res = client.get("/api/v1/trains")
    assert res.status_code == 200
    trains = res.json()
    assert len(trains) > 0
    assert any(t["train_no"] == "12002" for t in trains)
    print("PASS")

    print("[Test 7] GET /api/v1/trains/12002 ... ", end="")
    res = client.get("/api/v1/trains/12002")
    assert res.status_code == 200
    status_data = res.json()
    assert status_data["train_no"] == "12002"
    assert len(status_data["route"]) > 0
    print("PASS")

    # 5. Test Scenario Player & Cascade Simulation
    print("[Test 8] GET /api/v1/cascade/scenario ... ", end="")
    res = client.get("/api/v1/cascade/scenario")
    assert res.status_code == 200
    assert "scenario_name" in res.json()
    print("PASS")

    # Advance scenario step to step 1
    print("[Test 9] POST /api/v1/cascade/scenario/next ... ", end="")
    res = client.post("/api/v1/cascade/scenario/next")
    assert res.status_code == 200
    assert res.json()["step"] == 1
    print("PASS")

    print("[Test 10] GET /api/v1/disruptions ... ", end="")
    res = client.get("/api/v1/disruptions")
    assert res.status_code == 200
    disruptions = res.json()
    assert len(disruptions) > 0
    disp_id = disruptions[0]["id"]
    print("PASS")

    print("[Test 11] GET /api/v1/cascade/simulate ... ", end="")
    res = client.get(f"/api/v1/cascade/simulate?disruption_id={disp_id}")
    assert res.status_code == 200
    assert res.json()["root_disruption_id"] == disp_id
    print("PASS")

    # 6. Test Rerouting Advisories
    print("[Test 12] GET /api/v1/rerouting ... ", end="")
    res = client.get(f"/api/v1/rerouting?disruption_id={disp_id}")
    assert res.status_code == 200
    assert len(res.json()) > 0
    print("PASS")

    # 7. Test RAC Confirmation Prediction
    print("[Test 13] POST /api/v1/rac/predict ... ", end="")
    query_payload = {
        "train_no": "22415",
        "from_station": "NDLS",
        "to_station": "ALJN",
        "date": "2026-06-15",
        "current_waitlist_position": 12,
        "current_rac_count": 8,
        "days_to_journey": 4,
        "quota": "GN"
    }
    res = client.post("/api/v1/rac/predict", json=query_payload)
    assert res.status_code == 200
    prediction = res.json()
    assert 0.0 <= prediction["confirmation_probability"] <= 1.0
    assert len(prediction["key_factors"]) > 0
    print("PASS")

    # 8. Test Audit Chain Verification
    print("[Test 14] GET /api/v1/audit ... ", end="")
    res = client.get("/api/v1/audit")
    assert res.status_code == 200
    assert len(res.json()) > 0
    print("PASS")

    print("[Test 15] GET /api/v1/audit/verify ... ", end="")
    res = client.get("/api/v1/audit/verify")
    assert res.status_code == 200
    assert res.json()["chain_valid"] is True
    print("PASS")

    # Reset scenario step back to step 0
    print("\nResetting scenario steps...")
    client.post("/api/v1/cascade/scenario/reset")

    print("\n====================================================")
    print("    ALL INTEGRITY TESTS PASSED SUCCESSFULLY! (15/15) ")
    print("====================================================")

if __name__ == "__main__":
    run_tests()
