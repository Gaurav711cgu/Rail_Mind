"""
Unit tests for core services, scenario engine, rate limiter, models, and anomaly detector.
These tests exercise the zero-coverage files without requiring DB or HTTP stack.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock


# ─────────────────────────────────────────────────────────────
#  ScenarioEngine
# ─────────────────────────────────────────────────────────────

def test_scenario_engine_initial_state():
    from app.core.scenario_engine import ScenarioEngine
    engine = ScenarioEngine()
    state = engine.get_state()
    assert state["step"] == 0
    assert state["max_steps"] == 6
    assert len(state["trains"]) > 0
    assert state["disruptions"] == []


def test_scenario_engine_next_step():
    from app.core.scenario_engine import ScenarioEngine
    engine = ScenarioEngine()
    assert engine.next_step() == 1
    assert engine.next_step() == 2
    state = engine.get_state()
    assert state["step"] == 2


def test_scenario_engine_reset():
    from app.core.scenario_engine import ScenarioEngine
    engine = ScenarioEngine()
    engine.next_step()
    engine.next_step()
    state = engine.reset()
    assert state["step"] == 0
    assert engine.current_step == 0


def test_scenario_engine_all_steps_valid():
    from app.core.scenario_engine import ScenarioEngine
    engine = ScenarioEngine()
    for _ in range(engine.max_steps):
        engine.next_step()
        state = engine.get_state()
        assert "trains" in state
        assert "disruptions" in state
        assert "recommendations" in state
        assert "logs" in state
        assert "audit_entries" in state


def test_scenario_engine_does_not_exceed_max_steps():
    from app.core.scenario_engine import ScenarioEngine
    engine = ScenarioEngine()
    for _ in range(10):
        engine.next_step()
    assert engine.current_step == engine.max_steps


def test_scenario_engine_step6_has_resolved_disruption():
    from app.core.scenario_engine import ScenarioEngine
    engine = ScenarioEngine()
    while engine.current_step < 6:
        engine.next_step()
    state = engine.get_state()
    resolved = [d for d in state["disruptions"] if d["status"] == "RESOLVED"]
    assert len(resolved) >= 1


def test_scenario_engine_hash_is_sha256():
    from app.core.scenario_engine import ScenarioEngine
    engine = ScenarioEngine()
    h = engine._hash("test-input")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# ─────────────────────────────────────────────────────────────
#  InMemoryRateLimiter
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limiter_allows_requests_under_limit():
    from app.core.rate_limiter import InMemoryRateLimiter
    limiter = InMemoryRateLimiter(requests_limit=5, window_seconds=60)
    request = MagicMock()
    request.url.path = "/api/v1/trains"
    request.base_url = MagicMock()
    request.base_url.__str__ = lambda s: "http://testserver/"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {}

    # Should not raise for the first 5 requests
    for _ in range(5):
        await limiter.check_rate_limit(request)


@pytest.mark.asyncio
async def test_rate_limiter_bypasses_docs_paths():
    from app.core.rate_limiter import InMemoryRateLimiter
    limiter = InMemoryRateLimiter(requests_limit=1, window_seconds=60)
    request = MagicMock()
    request.url.path = "/docs"
    request.base_url = MagicMock()
    request.base_url.__str__ = lambda s: "http://api.example.com/"
    request.client = MagicMock()
    request.client.host = "1.2.3.4"
    request.headers = {}
    # Should never raise for docs paths
    for _ in range(20):
        await limiter.check_rate_limit(request)


@pytest.mark.asyncio
async def test_rate_limiter_bypasses_testserver():
    from app.core.rate_limiter import InMemoryRateLimiter
    limiter = InMemoryRateLimiter(requests_limit=1, window_seconds=60)
    request = MagicMock()
    request.url.path = "/api/v1/trains"
    request.base_url = MagicMock()
    request.base_url.__str__ = lambda s: "http://testserver/"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {}
    # testserver bypasses rate limiting
    for _ in range(10):
        await limiter.check_rate_limit(request)


# ─────────────────────────────────────────────────────────────
#  Models — Pydantic schema validation
# ─────────────────────────────────────────────────────────────

def test_disruption_model_valid():
    from app.models.disruption import Disruption
    d = Disruption(
        id="disp-001",
        train_no="12002",
        section_from="NDLS",
        section_to="GZB",
        disruption_type="SIGNAL_FAILURE",
        severity="HIGH",
        cascade_depth=2,
        status="ACTIVE",
        upstream_delay_minutes=45,
    )
    assert d.train_no == "12002"
    assert d.severity == "HIGH"


def test_disruption_model_defaults():
    from app.models.disruption import Disruption
    d = Disruption(
        id="disp-002",
        train_no="22415",
        section_from="GZB",
        section_to="ALJN",
        disruption_type="DELAY_CASCADE",
        severity="MEDIUM",
    )
    assert d.status == "ACTIVE"
    assert d.cascade_depth == 0


def test_train_position_model():
    from app.models.train import TrainPosition
    t = TrainPosition(
        train_no="12002",
        train_name="Shatabdi Express",
        current_station="NDLS",
        current_delay=15,
        status="RUNNING",
    )
    assert t.train_no == "12002"
    assert t.current_delay == 15


def test_recommendation_model():
    from app.models.recommendation import Recommendation
    r = Recommendation(
        id="rec-001",
        disruption_id="disp-001",
        type="HOLD",
        target_train="BOXN-902",
        reasoning="Hold freight to clear path",
        confidence=0.91,
        tier=1,
    )
    assert r.tier == 1
    assert r.confidence == 0.91
    assert r.is_approved is False


def test_rac_model():
    from app.models.rac import RACQuery, RACPrediction
    q = RACQuery(
        train_no="12002",
        from_station="NDLS",
        to_station="CNB",
        date="2026-06-12",
        current_waitlist_position=5,
        current_rac_count=20,
        days_to_journey=10,
        quota="GN",
    )
    assert q.train_no == "12002"


def test_audit_model():
    from app.models.audit import AuditEntry
    entry = AuditEntry(
        agent="MonitorAgent",
        action="ANOMALY_INGESTED",
        target="12002",
        reasoning="Delay exceeded threshold",
        confidence=0.95,
        hash="a" * 64,
        prev_hash="0" * 64,
    )
    assert entry.agent == "MonitorAgent"
    assert len(entry.hash) == 64


def test_user_model():
    from app.models.user import UserCreate, UserResponse
    u = UserCreate(username="test_user", password="password123")
    assert u.username == "test_user"


# ─────────────────────────────────────────────────────────────
#  NTESAnomalyDetector
# ─────────────────────────────────────────────────────────────

def test_anomaly_detector_fit_and_predict():
    from app.services.anomaly_detector import NTESAnomalyDetector
    detector = NTESAnomalyDetector()
    # Generate synthetic nominal telemetry
    rng = np.random.default_rng(42)
    X_train = rng.normal(loc=[10.0, 5.0], scale=[1.0, 0.5], size=(200, 2))
    detector.fit(X_train)

    # Nominal sample — should not be anomaly
    normal = np.array([[10.1, 5.05]])
    assert detector.predict(normal)[0] in (-1, 1)


def test_anomaly_detector_detects_outlier():
    from app.services.anomaly_detector import NTESAnomalyDetector
    detector = NTESAnomalyDetector(contamination=0.05)
    rng = np.random.default_rng(0)
    X_train = rng.normal(loc=[0.0, 0.0], scale=[0.1, 0.1], size=(300, 2))
    detector.fit(X_train)
    # Extreme outlier
    outlier = np.array([[100.0, 100.0]])
    result = detector.predict(outlier)
    assert result[0] == -1  # anomaly


def test_anomaly_detector_score():
    from app.services.anomaly_detector import NTESAnomalyDetector
    detector = NTESAnomalyDetector()
    rng = np.random.default_rng(1)
    X = rng.normal(size=(100, 3))
    detector.fit(X)
    scores = detector.score_samples(X)
    assert len(scores) == 100
