import pytest
from app.agents.monitor_agent import MonitorAgent
from app.agents.conflict_detector import ConflictDetector
from app.agents.cascade_predictor import CascadePredictor
from app.agents.dispatch_agent import DispatchAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.audit_agent import AuditAgent

@pytest.mark.asyncio
async def test_monitor_agent_nominal():
    agent = MonitorAgent()
    state = {
        "trains": [
            {"train_no": "12002", "current_station": "NDLS", "current_delay": 5, "status": "RUNNING"},
            {"train_no": "22415", "current_station": "ALJN", "current_delay": 0, "status": "RUNNING"}
        ],
        "disruptions": []
    }
    updates, confidence, reasoning = await agent.process(state)
    assert not updates.get("disruptions")
    assert confidence == 1.0
    assert "within schedule variance" in reasoning

@pytest.mark.asyncio
async def test_monitor_agent_anomaly():
    agent = MonitorAgent()
    state = {
        "trains": [
            {"train_no": "12002", "current_station": "NDLS", "current_delay": 25, "status": "HELD"},
            {"train_no": "22415", "current_station": "ALJN", "current_delay": 0, "status": "RUNNING"}
        ],
        "disruptions": []
    }
    updates, confidence, reasoning = await agent.process(state)
    assert len(updates.get("disruptions", [])) == 1
    assert confidence == 0.98
    assert "exceeds" in reasoning

@pytest.mark.asyncio
async def test_conflict_detector():
    agent = ConflictDetector()
    state = {
        "disruptions": [
            {
                "id": "disp-001", 
                "train_no": "12002", 
                "section_from": "NDLS", 
                "section_to": "GZB", 
                "status": "ACTIVE",
                "severity": "MEDIUM"
            }
        ],
        "recommendations": []
    }
    updates, confidence, reasoning = await agent.process(state)
    assert confidence == 0.94
    assert "conflict" in reasoning.lower()

@pytest.mark.asyncio
async def test_cascade_predictor():
    agent = CascadePredictor()
    state = {
        "disruptions": [
            {
                "id": "disp-001", 
                "train_no": "12002", 
                "section_from": "NDLS", 
                "section_to": "ALJN", 
                "status": "ACTIVE",
                "severity": "HIGH"
            }
        ],
        "trains": [
            {"train_no": "22415", "current_station": "ALJN", "current_delay": 0, "status": "RUNNING"}
        ]
    }
    updates, confidence, reasoning = await agent.process(state)
    assert confidence == 0.91
    assert "cascade" in reasoning.lower()

@pytest.mark.asyncio
async def test_dispatch_agent():
    agent = DispatchAgent()
    state = {
        "disruptions": [
            {
                "id": "disp-001", 
                "train_no": "12002", 
                "section_from": "NDLS", 
                "section_to": "ALJN", 
                "status": "ACTIVE",
                "severity": "HIGH"
            }
        ],
        "trains": [
            {"train_no": "12002", "current_station": "NDLS", "current_delay": 40, "status": "HELD"},
            {"train_no": "BOXN-902", "current_station": "GZB", "current_delay": 10, "status": "RUNNING"}
        ],
        "recommendations": []
    }
    updates, confidence, reasoning = await agent.process(state)
    assert len(updates.get("recommendations", [])) == 1
    assert confidence > 0.5
    assert "BOXN-902" in reasoning or "hold" in reasoning.lower()

@pytest.mark.asyncio
async def test_notification_agent():
    agent = NotificationAgent()
    state = {
        "disruptions": [
            {"id": "disp-001", "train_no": "12002", "section_from": "NDLS", "section_to": "ALJN", "status": "ACTIVE"}
        ],
        "recommendations": [
            {"id": "rec-001", "type": "HOLD", "target_train": "BOXN-902", "confidence": 0.78, "is_approved": False}
        ]
    }
    updates, confidence, reasoning = await agent.process(state)
    assert confidence == 0.90
    assert "disseminated" in reasoning.lower() or "alerted" in reasoning.lower() or "dispatched" in reasoning.lower()

@pytest.mark.asyncio
async def test_audit_agent():
    agent = AuditAgent()
    state = {
        "logs": ["Test log message"],
        "audit_chain": []
    }
    updates, confidence, reasoning = await agent.process(state)
    assert len(updates.get("audit_chain", [])) == 1
    assert confidence == 1.0
    assert "sealed" in reasoning.lower()
