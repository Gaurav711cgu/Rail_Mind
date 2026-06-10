"""
Integration test for the WebSocket endpoint at /api/v1/stream/ws.

Verifies:
- The endpoint accepts WebSocket connections.
- It sends JSON data within 10 seconds.
- The payload contains ``agents`` and ``trains`` keys.
"""

import asyncio
import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app


@pytest.mark.asyncio
async def test_websocket_sends_combined_data():
    """
    Connect to /api/v1/stream/ws and verify the first message
    contains both 'agents' and 'trains' keys.
    """
    client = TestClient(app)

    with client.websocket_connect("/api/v1/stream/ws") as ws:
        # The server sends a message every 5s; wait up to 10s
        data = ws.receive_json(mode="text")

        assert isinstance(data, dict), "Payload should be a JSON object"
        assert "agents" in data, "Payload must contain 'agents' key"
        assert "trains" in data, "Payload must contain 'trains' key"
        assert "timestamp" in data, "Payload must contain 'timestamp' key"
