"""
SSE + WebSocket endpoints for real-time agent events and train position updates.
Falls back gracefully when Redis is unavailable (memory-mode).
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.agents.orchestrator import orchestrator
from app.core.scenario_engine import scenario_engine
from app.services.live_rail_data import live_rail_data

router = APIRouter()


# --------------------------------------------------------------------------- #
#  SSE generators (unchanged — kept for backward compatibility)                #
# --------------------------------------------------------------------------- #


async def _agent_event_generator() -> AsyncGenerator[str, None]:
    """
    Yields SSE-formatted agent health snapshots every 5 seconds.
    On each tick, flushes the current agent_health dict from the orchestrator.
    """
    while True:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents": orchestrator.agent_health,
        }
        yield f"data: {json.dumps(payload)}\n\n"
        await asyncio.sleep(5)


async def _position_event_generator() -> AsyncGenerator[str, None]:
    """
    Yields SSE-formatted train position updates every 10 seconds.
    Uses RapidAPI-backed live telemetry when configured, with scenario fallback.
    """
    while True:
        trains = await live_rail_data.live_watchlist_snapshot(scenario_engine.get_state().get("trains", []))
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trains": trains,
        }
        yield f"data: {json.dumps(payload)}\n\n"
        await asyncio.sleep(10)


@router.get("/agents")
async def stream_agents():
    """
    SSE stream of agent health + last-run metadata.
    Subscribe with: new EventSource('/api/v1/stream/agents')
    """
    return StreamingResponse(
        _agent_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/positions")
async def stream_positions():
    """
    SSE stream of train GPS/status positions.
    Subscribe with: new EventSource('/api/v1/stream/positions')
    """
    return StreamingResponse(
        _position_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# --------------------------------------------------------------------------- #
#  WebSocket endpoint — combined agent health + train positions                #
# --------------------------------------------------------------------------- #


@router.websocket("/ws")
async def websocket_stream(ws: WebSocket):
    """
    WebSocket endpoint at ``/api/v1/stream/ws``.

    Sends a combined JSON payload every 5 seconds containing:
    - ``agents``: current agent health snapshot from the orchestrator.
    - ``trains``: live train position data.
    """
    await ws.accept()
    try:
        while True:
            trains = await live_rail_data.live_watchlist_snapshot(scenario_engine.get_state().get("trains", []))
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agents": orchestrator.agent_health,
                "trains": trains,
            }
            await ws.send_json(payload)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    except Exception:
        await ws.close()
