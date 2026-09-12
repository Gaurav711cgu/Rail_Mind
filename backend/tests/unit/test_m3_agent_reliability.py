import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.audit_agent import AuditAgent, verify_chain, MAX_AUDIT_CHAIN_SIZE
from app.agents.dispatch_agent import DispatchAgent, extract_json_payload, _build_dispatch_prompt
from app.core.rate_limiter import InMemoryRateLimiter
from app.agents.orchestrator import AgentOrchestrator
from app.ml.gnn_cascade import get_cached_gnn_model, RailwayGNN, _GNN_MODEL_CACHE
from app.agents.cascade_predictor import CascadePredictor


@pytest.mark.asyncio
async def test_audit_chain_sliding_window_bounding():
    """Verify that audit_chain is bounded to sliding window of max 100 entries."""
    agent = AuditAgent()

    # Pre-populate chain with 120 synthetic entries
    synthetic_chain = []
    prev_h = "0" * 64
    for i in range(120):
        h = f"{i:064x}"
        synthetic_chain.append(
            {
                "timestamp": "2026-09-12T12:00:00+00:00",
                "agent": "AuditAgent",
                "action": "HOLD",
                "target": f"rec-{i}",
                "reasoning": f"Holding train {i}",
                "confidence": 0.95,
                "tier": 1,
                "prev_hash": prev_h,
                "hash": h,
            }
        )
        prev_h = h

    state = {
        "audit_chain": synthetic_chain,
        "recommendations": [
            {
                "id": "rec-new-999",
                "agent_name": "DispatchAgent",
                "type": "PROCEED",
                "reasoning": "Track clear",
                "confidence": 0.99,
                "tier": 1,
            }
        ],
        "disruptions": [],
    }

    with patch("app.agents.audit_agent.persist_audit_entries", new_callable=AsyncMock) as mock_persist:
        updates, conf, reasoning = await agent.process(state)

    chain = updates["audit_chain"]
    # Chain must be bounded to MAX_AUDIT_CHAIN_SIZE (100)
    assert len(chain) == MAX_AUDIT_CHAIN_SIZE
    assert len(chain) <= 100
    # verify_chain on sliding window returns True
    is_valid, fail_idx, msg = verify_chain(chain)
    assert is_valid is True
    # Pruned entries must be sent to persist_audit_entries
    assert mock_persist.called


def test_in_memory_rate_limiter_ttl_eviction():
    """Verify that inactive IP keys are evicted after TTL to eliminate memory leaks."""
    limiter = InMemoryRateLimiter(
        requests_limit=5,
        window_seconds=1,
        ttl_seconds=2,
        cleanup_interval_seconds=1,
    )

    t0 = 1000.0
    # Simulate requests from 100 unique scanner IPs
    for i in range(100):
        ip = f"192.168.1.{i}"
        limiter.history[ip] = [t0]
        limiter.last_seen[ip] = t0

    assert len(limiter.history) == 100
    assert len(limiter.last_seen) == 100

    # Advance time past TTL (t0 + 3s)
    t1 = t0 + 3.0
    evicted = limiter.evict_expired(now=t1)

    # All 100 inactive IP keys must be evicted
    assert evicted == 100
    assert len(limiter.history) == 0
    assert len(limiter.last_seen) == 0


def test_dispatch_agent_robust_json_extraction():
    """Verify JSON extraction handles fences, preambles, and postambles without error."""
    # 1. Standard raw JSON
    raw1 = '{"action": "HOLD", "target_train": "12002", "confidence": 0.92}'
    d1 = extract_json_payload(raw1)
    assert d1["action"] == "HOLD"

    # 2. Markdown fence with json tag
    raw2 = '```json\n{"action": "PROCEED", "target_train": "22415", "confidence": 0.88}\n```'
    d2 = extract_json_payload(raw2)
    assert d2["action"] == "PROCEED"

    # 3. Model preamble and postamble around fence
    raw3 = (
        "Here is the recommended dispatch decision based on the current situation:\n"
        "```json\n"
        '{\n  "action": "ESCALATE",\n  "target_train": "12004",\n  "confidence": 0.60\n}\n'
        "```\n"
        "Let me know if you need additional assistance."
    )
    d3 = extract_json_payload(raw3)
    assert d3["action"] == "ESCALATE"

    # 4. Raw text with braces but no fences
    raw4 = (
        "Analysis complete. Result: "
        '{"action": "HOLD", "reasoning": "Passenger priority applies.", "confidence": 0.90} '
        "Logged to controller ledger."
    )
    d4 = extract_json_payload(raw4)
    assert d4["action"] == "HOLD"
    assert d4["confidence"] == 0.90


def test_dispatch_prompt_xml_isolation():
    """Verify that untrusted input is strictly delimited within XML tags."""
    disruption = {
        "id": "DISP-001",
        "train_no": "12002",
        "section_from": "NDLS",
        "section_to": "GZB",
        "disruption_type": "SIGNAL_FAILURE",
        "severity": "HIGH",
        "cascade_depth": 2,
    }
    trains = [
        {"train_no": "12002", "train_name": "Shatabdi", "current_delay": 35, "status": "HELD", "current_station": "NDLS"}
    ]
    prompt = _build_dispatch_prompt(disruption, trains, "Cascade depth 2")

    assert "<untrusted_disruption>" in prompt
    assert "</untrusted_disruption>" in prompt
    assert "<untrusted_trains>" in prompt
    assert "</untrusted_trains>" in prompt
    assert "<untrusted_cascade>" in prompt
    assert "</untrusted_cascade>" in prompt
    assert "SECURITY NOTICE" in prompt


@pytest.mark.asyncio
async def test_dispatch_agent_exponential_backoff():
    """Verify that DispatchAgent retries API calls with exponential backoff on transient errors."""
    agent = DispatchAgent()

    call_count = 0

    async def flaky_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("HTTP 429 Too Many Requests: Rate limit exceeded")
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='{"action": "HOLD", "confidence": 0.89, "reasoning": "ok"}')]
        return mock_msg

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=flaky_create)

    with patch.object(agent, "_get_client", return_value=mock_client):
        action, reasoning, conf, crew, saving = await agent._llm_recommend(
            {"id": "d1"}, [], "cascade"
        )

    assert call_count == 3
    assert action == "HOLD"
    assert conf == 0.89


@pytest.mark.asyncio
async def test_orchestrator_30s_timeout():
    """Verify orchestrator wraps LangGraph with 30.0s timeout and handles timeout gracefully."""
    orchestrator = AgentOrchestrator()

    async def hanging_ainvoke(*args, **kwargs):
        await asyncio.sleep(100.0)
        return {}

    with patch("app.agents.orchestrator._graph.ainvoke", side_effect=hanging_ainvoke):
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError("Execution timed out")):
            result = await orchestrator.run_pipeline({"trains": [], "disruptions": []})

    assert any("timed out" in log.lower() for log in result.get("logs", []))


def test_gnn_model_singleton_cache_and_safe_deserialization():
    """Verify RailwayGNN model weights cache reuses singleton and enforces weights_only=True."""
    mock_model = RailwayGNN(
        node_feat_dim=8,
        edge_feat_dim=6,
        hidden_dim=32,
        n_sage_layers=1,
        n_gat_heads=1,
    )
    mock_checkpoint = {
        "state_dict": mock_model.state_dict(),
        "config": {
            "node_feat_dim": 8,
            "edge_feat_dim": 6,
            "hidden_dim": 32,
            "n_sage_layers": 1,
            "n_gat_heads": 1,
        },
    }

    # Clear cache before test
    _GNN_MODEL_CACHE.clear()

    load_kwargs_history = []

    def mock_torch_load(filepath, **kwargs):
        load_kwargs_history.append(kwargs)
        return mock_checkpoint

    with patch("torch.load", side_effect=mock_torch_load):
        with patch("pathlib.Path.exists", return_value=True):
            # First load
            m1 = get_cached_gnn_model("/fake/path/gnn_cascade.pt")
            assert m1 is not None

            # Verify weights_only=True was enforced!
            assert len(load_kwargs_history) == 1
            assert load_kwargs_history[0].get("weights_only") is True

            # Second load: must be served from cache without calling torch.load again
            m2 = get_cached_gnn_model("/fake/path/gnn_cascade.pt")
            assert m2 is m1
            assert len(load_kwargs_history) == 1  # No second disk read!
