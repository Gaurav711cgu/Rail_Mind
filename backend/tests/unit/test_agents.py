"""
Unit tests for all 6 RailMind agents.
Tests real behavior, not hardcoded strings.
"""

import pytest
from app.agents.monitor_agent import MonitorAgent
from app.agents.conflict_detector import ConflictDetector
from app.agents.cascade_predictor import CascadePredictor
from app.agents.dispatch_agent import DispatchAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.audit_agent import AuditAgent


# ─────────────────────────────────────────────────────────────
#  MonitorAgent
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_monitor_agent_nominal():
    agent = MonitorAgent()
    state = {
        "trains": [
            {
                "train_no": "12002",
                "current_station": "NDLS",
                "current_delay": 5,
                "status": "RUNNING",
            },
            {
                "train_no": "22415",
                "current_station": "ALJN",
                "current_delay": 0,
                "status": "RUNNING",
            },
        ],
        "disruptions": [],
    }
    updates, confidence, reasoning = await agent.process(state)
    # No disruptions when delay < 20 min
    assert not updates.get("disruptions")
    assert confidence >= 0.90


@pytest.mark.asyncio
async def test_monitor_agent_anomaly_creates_disruption():
    agent = MonitorAgent()
    state = {
        "trains": [
            {"train_no": "12002", "current_station": "GZB", "current_delay": 45, "status": "HELD"},
        ],
        "disruptions": [],
    }
    updates, confidence, reasoning = await agent.process(state)
    new_disruptions = updates.get("disruptions", [])
    assert len(new_disruptions) >= 1
    assert new_disruptions[0]["train_no"] == "12002"
    assert new_disruptions[0]["status"] == "ACTIVE"
    assert confidence >= 0.85


@pytest.mark.asyncio
async def test_monitor_agent_no_duplicate_disruptions():
    """Should not add a second disruption for a train already in disruptions list."""
    agent = MonitorAgent()
    existing_disruption = {
        "id": "disp-existing",
        "train_no": "12002",
        "section_from": "GZB",
        "section_to": "ALJN",
        "disruption_type": "DELAY_CASCADE",
        "severity": "HIGH",
        "status": "ACTIVE",
    }
    state = {
        "trains": [
            {"train_no": "12002", "current_station": "GZB", "current_delay": 45, "status": "HELD"},
        ],
        "disruptions": [existing_disruption],
    }
    updates, _, _ = await agent.process(state)
    disruptions = updates.get("disruptions", [existing_disruption])
    # Should not double-add
    assert sum(1 for d in disruptions if d["train_no"] == "12002") == 1


# ─────────────────────────────────────────────────────────────
#  ConflictDetector
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_conflict_detector_with_active_disruption():
    agent = ConflictDetector()
    state = {
        "disruptions": [
            {
                "id": "disp-001",
                "train_no": "12002",
                "section_from": "NDLS",
                "section_to": "GZB",
                "status": "ACTIVE",
                "severity": "MEDIUM",
            }
        ],
        "recommendations": [],
    }
    updates, confidence, reasoning = await agent.process(state)
    assert confidence > 0.0
    assert "conflict" in reasoning.lower() or "section" in reasoning.lower()


@pytest.mark.asyncio
async def test_conflict_detector_no_disruptions():
    agent = ConflictDetector()
    state = {"disruptions": [], "recommendations": []}
    updates, confidence, reasoning = await agent.process(state)
    assert confidence >= 0.95


# ─────────────────────────────────────────────────────────────
#  CascadePredictor
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cascade_predictor_runs_bfs():
    """BFS should propagate from a known station and return cascade data."""
    agent = CascadePredictor()
    state = {
        "disruptions": [
            {
                "id": "disp-001",
                "train_no": "12002",
                "section_from": "NDLS",  # Known station in the graph
                "section_to": "GZB",
                "status": "ACTIVE",
                "severity": "HIGH",
                "upstream_delay_minutes": 60,
            }
        ],
        "trains": [
            {
                "train_no": "22415",
                "current_station": "GZB",
                "current_delay": 0,
                "status": "RUNNING",
                "train_type": "SUPERFAST",
            },
        ],
    }
    updates, confidence, reasoning = await agent.process(state)
    assert confidence > 0.0
    # Disruption should be updated with cascade_depth
    updated_disruptions = updates.get("disruptions", [])
    assert len(updated_disruptions) >= 1
    assert updated_disruptions[0].get("cascade_depth", 0) >= 0


@pytest.mark.asyncio
async def test_cascade_predictor_no_disruptions():
    agent = CascadePredictor()
    state = {"disruptions": [], "trains": []}
    updates, confidence, reasoning = await agent.process(state)
    assert confidence >= 0.95
    assert not updates


@pytest.mark.asyncio
async def test_cascade_predictor_unknown_station():
    """Unknown station should not crash — returns low confidence."""
    agent = CascadePredictor()
    state = {
        "disruptions": [
            {
                "id": "disp-002",
                "train_no": "99999",
                "section_from": "UNKNOWN_STN",
                "section_to": "NOWHERE",
                "status": "ACTIVE",
                "severity": "HIGH",
                "upstream_delay_minutes": 45,
            }
        ],
        "trains": [],
    }
    updates, confidence, reasoning = await agent.process(state)
    # Should not raise — just return low confidence
    assert confidence <= 0.75


# ─────────────────────────────────────────────────────────────
#  DispatchAgent
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dispatch_agent_generates_recommendation():
    agent = DispatchAgent()
    state = {
        "disruptions": [
            {
                "id": "disp-001",
                "train_no": "12002",
                "section_from": "NDLS",
                "section_to": "GZB",
                "status": "ACTIVE",
                "severity": "HIGH",
                "disruption_type": "DELAY_CASCADE",
            }
        ],
        "trains": [
            {
                "train_no": "12002",
                "current_station": "NDLS",
                "current_delay": 40,
                "status": "HELD",
                "train_type": "SUPERFAST",
            },
            {
                "train_no": "BOXN-902",
                "current_station": "GZB",
                "current_delay": 5,
                "status": "RUNNING",
                "train_type": "FREIGHT",
            },
        ],
        "recommendations": [],
    }
    updates, confidence, reasoning = await agent.process(state)
    recs = updates.get("recommendations", [])
    assert len(recs) >= 1
    rec = recs[0]
    # Must have required fields
    assert rec.get("type") in ("HOLD", "PROCEED", "REROUTE_FREIGHT", "ESCALATE")
    assert rec.get("confidence") is not None
    assert rec.get("tier") in (1, 2)
    assert rec.get("reasoning")
    # Confidence must be in valid range
    assert 0.0 <= rec["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_dispatch_agent_safety_critical_always_escalates():
    """SIGNAL_FAILURE must always escalate, never auto-execute."""
    agent = DispatchAgent()
    state = {
        "disruptions": [
            {
                "id": "disp-spad",
                "train_no": "12002",
                "section_from": "GZB",
                "section_to": "ALJN",
                "status": "ACTIVE",
                "severity": "CRITICAL",
                "disruption_type": "SIGNAL_FAILURE",  # safety-critical
            }
        ],
        "trains": [],
        "recommendations": [],
    }
    updates, confidence, reasoning = await agent.process(state)
    recs = updates.get("recommendations", [])
    assert len(recs) >= 1
    # Safety-critical must always be ESCALATE
    assert recs[0]["type"] == "ESCALATE"
    assert recs[0]["tier"] == 2
    assert updates.get("escalated") is True


@pytest.mark.asyncio
async def test_dispatch_agent_no_disruptions():
    agent = DispatchAgent()
    state = {"disruptions": [], "trains": [], "recommendations": []}
    updates, confidence, reasoning = await agent.process(state)
    assert confidence >= 0.95
    assert not updates.get("recommendations")


# ─────────────────────────────────────────────────────────────
#  NotificationAgent
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_notification_agent_generates_advisory():
    agent = NotificationAgent()
    state = {
        "disruptions": [
            {
                "id": "disp-001",
                "train_no": "12002",
                "section_from": "NDLS",
                "section_to": "GZB",
                "status": "ACTIVE",
            }
        ],
        "recommendations": [
            {
                "id": "rec-001",
                "type": "HOLD",
                "target_train": "12002",
                "confidence": 0.91,
                "tier": 1,
                "is_approved": False,
            }
        ],
    }
    updates, confidence, reasoning = await agent.process(state)
    assert confidence > 0.0
    assert reasoning  # Must have some reasoning text


# ─────────────────────────────────────────────────────────────
#  AuditAgent — per-entry hash chain
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_agent_creates_entries():
    agent = AuditAgent()
    state = {
        "logs": ["[MonitorAgent] Delay detected", "[DispatchAgent] HOLD issued"],
        "audit_chain": [],
        "recommendations": [
            {
                "id": "rec-001",
                "type": "HOLD",
                "target_train": "12002",
                "reasoning": "Hold freight to clear passenger path.",
                "confidence": 0.91,
                "tier": 1,
            }
        ],
        "disruptions": [
            {
                "id": "disp-001",
                "train_no": "12002",
                "section_from": "GZB",
                "section_to": "ALJN",
                "disruption_type": "DELAY_CASCADE",
                "severity": "HIGH",
                "cascade_depth": 2,
            }
        ],
    }
    updates, confidence, reasoning = await agent.process(state)
    chain = updates.get("audit_chain", [])
    assert len(chain) >= 1
    assert confidence == 1.0

    # Each entry must have a valid 64-char SHA-256 hash
    for entry in chain:
        assert "hash" in entry
        assert len(entry["hash"]) == 64
        assert "prev_hash" in entry
        assert len(entry["prev_hash"]) == 64


@pytest.mark.asyncio
async def test_audit_agent_chain_integrity():
    """Running two consecutive audit cycles should produce a valid linked chain."""
    agent = AuditAgent()

    state1 = {
        "logs": ["[MonitorAgent] Cycle 1"],
        "audit_chain": [],
        "recommendations": [],
        "disruptions": [
            {
                "id": "disp-cycle1",
                "train_no": "12002",
                "section_from": "NDLS",
                "section_to": "GZB",
                "disruption_type": "DELAY_CASCADE",
                "severity": "MEDIUM",
                "cascade_depth": 1,
            }
        ],
    }
    updates1, _, _ = await agent.process(state1)
    chain1 = updates1.get("audit_chain", [])

    state2 = {
        "logs": ["[DispatchAgent] Cycle 2"],
        "audit_chain": chain1,
        "recommendations": [
            {
                "id": "rec-cycle2",
                "type": "PROCEED",
                "target_train": "22415",
                "reasoning": "Clear path confirmed.",
                "confidence": 0.94,
                "tier": 1,
            }
        ],
        "disruptions": [],
    }
    updates2, _, _ = await agent.process(state2)
    chain2 = updates2.get("audit_chain", [])

    # Chain should grow
    assert len(chain2) > len(chain1)

    # Each entry's prev_hash must equal the preceding entry's hash
    for i in range(1, len(chain2)):
        assert chain2[i]["prev_hash"] == chain2[i - 1]["hash"], (
            f"Chain break between entry {i - 1} and {i}"
        )
