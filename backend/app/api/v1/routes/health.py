from fastapi import APIRouter
from datetime import datetime
from app.config import settings
from app.services.live_rail_data import live_rail_data

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "scenario_mode": settings.SCENARIO_MODE
    }


@router.get("/health/data-freshness")
async def data_freshness():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "live_data_provider": settings.LIVE_DATA_PROVIDER,
        "rapidapi_configured": bool(settings.RAPIDAPI_IRCTC_KEY),
        "real_data_required": settings.REAL_DATA_REQUIRED,
        "scenario_mode": settings.SCENARIO_MODE,
        "watchlist": live_rail_data.watchlist(),
        "status": "live" if settings.RAPIDAPI_IRCTC_KEY else "scenario-fallback",
    }
