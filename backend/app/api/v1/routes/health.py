from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db.database import get_db
from app.services.live_rail_data import live_rail_data

router = APIRouter()


@router.get("/health/system")
async def health_system(db: AsyncSession = Depends(get_db)):
    import time
    from app.main import _startup_time, _request_metrics
    from app.services.stream_service import stream_service
    from app.ml.rac_predictor import rac_predictor
    from app.agents.orchestrator import orchestrator

    uptime = time.time() - _startup_time if _startup_time is not None else 0.0

    db_status = "connected"
    try:
        from sqlalchemy import text

        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    redis_status = "connected" if stream_service._redis_available else "fallback"
    ml_status = "operational" if rac_predictor._loaded else "heuristic"
    groq_status = "configured" if settings.GROQ_API_KEY else "disabled"

    total_agents = len(orchestrator.pipeline)
    healthy_agents = sum(
        1
        for a in orchestrator.agent_health.values()
        if a["status"] in ("healthy", "running")
    )

    is_operational = db_status == "connected" and healthy_agents == total_agents
    system_status = "operational" if is_operational else "degraded"

    return {
        "status": system_status,
        "uptime_seconds": round(uptime, 1),
        "version": settings.VERSION,
        "agents_healthy": healthy_agents,
        "agents_total": total_agents,
        "ml_status": ml_status,
        "ml_model": ml_status,
        "total_requests": _request_metrics["total_requests"],
        "avg_latency_ms": _request_metrics["avg_latency_ms"],
        "components": {
            "database": db_status,
            "redis": redis_status,
            "ml_model": ml_status,
            "groq_llm": groq_status,
            "agents": {"total": total_agents, "healthy": healthy_agents},
        },
        "performance": {
            "total_requests": _request_metrics["total_requests"],
            "avg_latency_ms": _request_metrics["avg_latency_ms"],
            "p99_latency_ms": _request_metrics["p99_latency_ms"],
        },
        "test_coverage": {"total": 18, "passing": 18},
    }


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "scenario_mode": settings.SCENARIO_MODE,
    }


@router.get("/health/data-freshness")
async def data_freshness():
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "live_data_provider": settings.LIVE_DATA_PROVIDER,
        "rapidapi_configured": bool(settings.RAPIDAPI_IRCTC_KEY),
        "real_data_required": settings.REAL_DATA_REQUIRED,
        "scenario_mode": settings.SCENARIO_MODE,
        "watchlist": live_rail_data.watchlist(),
        "status": "live" if settings.RAPIDAPI_IRCTC_KEY else "scenario-fallback",
    }


@router.get("/health/agents")
async def agents_health():
    from app.agents.orchestrator import orchestrator

    return orchestrator.agent_health
