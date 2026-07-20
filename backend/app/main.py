from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.core.lifespan import lifespan
from app.api.middleware import performance_middleware, rate_limit_middleware
from app.api.exceptions import global_exception_handler
from app.api.v1.routes import (
    auth,
    trains,
    disruptions,
    cascade,
    rerouting,
    rac,
    audit,
    health,
    recommendations,
    stream,
    live,
)
from app.services.stream_service import stream_service
from app.ml.rac_predictor import rac_predictor

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Autonomous Agentic Dispatching & Punctuality Engine for Indian Railways. "
        "FAR AWAY 2026 — Agentic & Autonomous Systems × Railways."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type"],
)
app.middleware("http")(performance_middleware)
app.middleware("http")(rate_limit_middleware)

# Exception Handlers
app.add_exception_handler(Exception, global_exception_handler)

# Routes
app.include_router(health.router, tags=["Health"])
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["Health"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(trains.router, prefix=f"{settings.API_V1_STR}/trains", tags=["Trains"])
app.include_router(
    disruptions.router, prefix=f"{settings.API_V1_STR}/disruptions", tags=["Disruptions"]
)
app.include_router(cascade.router, prefix=f"{settings.API_V1_STR}/cascade", tags=["Cascade"])
app.include_router(rerouting.router, prefix=f"{settings.API_V1_STR}/rerouting", tags=["Rerouting"])
app.include_router(rac.router, prefix=f"{settings.API_V1_STR}/rac", tags=["RAC Predictor"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["Audit"])
app.include_router(
    recommendations.router,
    prefix=f"{settings.API_V1_STR}/recommendations",
    tags=["Recommendations"],
)
app.include_router(stream.router, prefix=f"{settings.API_V1_STR}/stream", tags=["Stream SSE"])
app.include_router(live.router, prefix=f"{settings.API_V1_STR}/live", tags=["Live Data"])


@app.get("/")
async def root():
    return {
        "product": "RailMind",
        "version": settings.VERSION,
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
        "scenario_mode": settings.SCENARIO_MODE,
        "redis_connected": stream_service._redis_available,
        "rac_model_loaded": rac_predictor._loaded,
    }
