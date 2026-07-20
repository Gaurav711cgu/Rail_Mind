import asyncio
import json
from fastapi import APIRouter, Depends, BackgroundTasks
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.database import get_db, DBLiveAgentRun, DBUser
from app.api.v1.routes.auth import get_current_user
from app.agents.orchestrator import AgentOrchestrator

router = APIRouter()

# Global state to prevent concurrent identical runs
_active_runs = {}


async def _run_agent_task(run_id: int, user_id: int):
    """Background task to run the agent in live mode."""
    try:
        from app.db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Mark as running
            run = await session.get(DBLiveAgentRun, run_id)
            if run:
                run.status = "RUNNING"
                await session.commit()

            # Execute graph
            orchestrator = AgentOrchestrator()
            await orchestrator.run_pipeline({"trains": [], "disruptions": []})

            # Mark complete
            run = await session.get(DBLiveAgentRun, run_id)
            if run:
                run.status = "COMPLETED"
                run.metrics_json = json.dumps({"status": "success", "user_id": user_id})
                run.completed_at = text("NOW()")
                await session.commit()
    except Exception as e:
        print(f"Agent run {run_id} failed: {e}")
        try:
            from app.db.database import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                run = await session.get(DBLiveAgentRun, run_id)
                if run:
                    run.status = "FAILED"
                    run.metrics_json = json.dumps({"error": str(e)})
                    run.completed_at = text("NOW()")
                    await session.commit()
        except Exception:
            pass
    finally:
        _active_runs.pop(run_id, None)


@router.post("/trigger")
async def trigger_live_mode(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    """Trigger a live data cycle (pull NTES, run agents)."""
    # Create run record
    new_run = DBLiveAgentRun(
        agent_name="LiveMonitorAgent",
        status="PENDING",
        metrics_json=json.dumps({"triggered_by": current_user.username}),
    )
    db.add(new_run)
    await db.commit()
    await db.refresh(new_run)

    _active_runs[new_run.id] = True
    background_tasks.add_task(_run_agent_task, new_run.id, current_user.id)

    return {"status": "triggered", "run_id": new_run.id}


@router.get("/stream")
async def live_mode_stream(db: AsyncSession = Depends(get_db)):
    """SSE endpoint for live status updates."""

    async def event_generator():
        while True:
            # For demonstration, check active runs and report status
            yield {
                "event": "message",
                "data": json.dumps(
                    {
                        "active_runs": len(_active_runs),
                        "timestamp": text("NOW()"),  # just indicating alive
                    }
                ),
            }
            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())
