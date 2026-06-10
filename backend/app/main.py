from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.db.database import init_db, AsyncSessionLocal, DBStation, DBSection, DBUser
from app.api.v1.routes import auth, trains, disruptions, cascade, rerouting, rac, audit, health, recommendations, stream
from app.api.v1.routes.auth import get_password_hash
from app.agents.orchestrator import orchestrator
from app.services.stream_service import stream_service
from app.ml.rac_predictor import rac_predictor   # triggers model load at startup


# --------------------------------------------------------------------------- #
#  Performance & Startup Metrics                                              #
# --------------------------------------------------------------------------- #
import time
_startup_time = None
_request_metrics = {
    "total_requests": 0,
    "avg_latency_ms": 0.0,
    "p99_latency_ms": 0.0,
    "_latencies": []
}


# --------------------------------------------------------------------------- #
#  Lifespan — startup / shutdown                                              #
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _startup_time
    _startup_time = time.time()

    # 1. Database
    print("[Lifespan] Initialising database schema...")
    await init_db()

    # 2. Redis Streams
    print("[Lifespan] Connecting to Redis Streams...")
    await stream_service.connect()

    # 3. Seed topology once
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(DBStation).limit(1))
        if not result.scalars().first():
            print("[Lifespan] Seeding railway topology...")
            stations = [
                DBStation(code="NDLS", name="New Delhi",        zone="NR",  division="DLI",  latitude=28.643, longitude=77.222, is_major_junction=True,  platform_count=16),
                DBStation(code="GZB",  name="Ghaziabad",        zone="NR",  division="DLI",  latitude=28.672, longitude=77.436, is_major_junction=True,  platform_count=6),
                DBStation(code="ALJN", name="Aligarh Jn",       zone="NR",  division="DLI",  latitude=27.892, longitude=78.078, is_major_junction=True,  platform_count=7),
                DBStation(code="CNB",  name="Kanpur Central",   zone="NCR", division="PRYJ", latitude=26.454, longitude=80.350, is_major_junction=True,  platform_count=10),
                DBStation(code="PRYJ", name="Prayagraj Jn",     zone="NCR", division="PRYJ", latitude=25.448, longitude=81.851, is_major_junction=True,  platform_count=12),
                DBStation(code="BSB",  name="Varanasi Jn",      zone="NR",  division="LKO",  latitude=25.317, longitude=82.973, is_major_junction=True,  platform_count=9),
                DBStation(code="HWH",  name="Howrah Jn",        zone="ER",  division="HWH",  latitude=22.583, longitude=88.342, is_major_junction=True,  platform_count=23),
                DBStation(code="MMCT", name="Mumbai Central",   zone="WR",  division="BCT",  latitude=18.971, longitude=72.820, is_major_junction=True,  platform_count=8),
                DBStation(code="BRC",  name="Vadodara Jn",      zone="WR",  division="BRC",  latitude=22.312, longitude=73.181, is_major_junction=True,  platform_count=6),
                DBStation(code="MAS",  name="Chennai Central",  zone="SR",  division="MAS",  latitude=13.082, longitude=80.275, is_major_junction=True,  platform_count=17),
                DBStation(code="SBC",  name="KSR Bengaluru",    zone="SWR", division="SBC",  latitude=12.978, longitude=77.572, is_major_junction=True,  platform_count=10),
                DBStation(code="SC",   name="Secunderabad Jn",  zone="SCR", division="SC",   latitude=17.431, longitude=78.501, is_major_junction=True,  platform_count=10),
            ]
            session.add_all(stations)

            sections = [
                DBSection(from_station="NDLS", to_station="GZB",  distance_km=25,  max_speed_kmh=110, signaling_type="ABSOLUTE_BLOCK", capacity_trains_per_hour=12),
                DBSection(from_station="GZB",  to_station="ALJN", distance_km=100, max_speed_kmh=130, signaling_type="ABSOLUTE_BLOCK", capacity_trains_per_hour=10),
                DBSection(from_station="ALJN", to_station="CNB",  distance_km=210, max_speed_kmh=130, signaling_type="ABSOLUTE_BLOCK", capacity_trains_per_hour=8),
                DBSection(from_station="CNB",  to_station="PRYJ", distance_km=190, max_speed_kmh=130, signaling_type="KAVACH",         capacity_trains_per_hour=15),
                DBSection(from_station="PRYJ", to_station="BSB",  distance_km=120, max_speed_kmh=110, signaling_type="KAVACH",         capacity_trains_per_hour=15),
                DBSection(from_station="BSB",  to_station="HWH",  distance_km=635, max_speed_kmh=100, signaling_type="ABSOLUTE_BLOCK", capacity_trains_per_hour=8),
                DBSection(from_station="NDLS", to_station="MMCT", distance_km=1384,max_speed_kmh=130, signaling_type="ABS",            capacity_trains_per_hour=10),
                DBSection(from_station="BRC",  to_station="MMCT", distance_km=391, max_speed_kmh=130, signaling_type="ABSOLUTE_BLOCK", capacity_trains_per_hour=12),
            ]
            session.add_all(sections)

            users = [
                DBUser(
                    username="controller_north",
                    email="controller@railmind.gov.in",
                    password_hash=get_password_hash("controller123"),
                    role="CONTROLLER",
                    zone="NR",
                ),
                DBUser(
                    username="admin",
                    email="admin@railmind.gov.in",
                    password_hash=get_password_hash("admin123"),
                    role="ADMIN",
                    zone="NR",
                ),
            ]
            session.add_all(users)
            await session.commit()
            print("[Lifespan] Topology seeded.")

    # 4. Start Redis stream consumer (background task)
    async def _on_telemetry_events(events):
        """Process telemetry events from the Redis stream."""
        for event_id, data in events:
            print(f"[StreamConsumer] event {event_id}: {data}")

    consumer_task = asyncio.create_task(
        stream_service.start_consumer(_on_telemetry_events)
    )
    print("[Lifespan] Redis stream consumer started.")

    # 5. Start agent background monitoring loop
    print("[Lifespan] Starting agent orchestrator...")
    await orchestrator.start()

    print("[Lifespan] RailMind engine ready.")
    yield

    # Shutdown
    print("[Lifespan] Shutting down...")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await orchestrator.stop()
    await stream_service.disconnect()
    print("[Lifespan] Clean shutdown complete.")


# --------------------------------------------------------------------------- #
#  App                                                                         #
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
#  Security middleware                                                         #
# --------------------------------------------------------------------------- #
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    finally:
        latency = (time.perf_counter() - start_time) * 1000.0
        _request_metrics["total_requests"] += 1
        n = _request_metrics["total_requests"]
        old_avg = _request_metrics["avg_latency_ms"]
        _request_metrics["avg_latency_ms"] = round(old_avg + (latency - old_avg) / n, 2)
        
        _request_metrics["_latencies"].append(latency)
        if len(_request_metrics["_latencies"]) > 100:
            _request_metrics["_latencies"].pop(0)
            
        sorted_l = sorted(_request_metrics["_latencies"])
        if sorted_l:
            idx = min(int(len(sorted_l) * 0.99), len(sorted_l) - 1)
            _request_metrics["p99_latency_ms"] = round(sorted_l[idx], 2)
        else:
            _request_metrics["p99_latency_ms"] = 0.0


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    from fastapi import HTTPException
    from app.core.rate_limiter import rate_limiter
    try:
        await rate_limiter.check_rate_limit(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


# --------------------------------------------------------------------------- #
#  Global exception handler — never leak stack traces to client               #
# --------------------------------------------------------------------------- #
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger("railmind").error(
        "Unhandled exception on %s %s: %s",
        request.method, request.url.path, exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. See server logs."},
    )


# --------------------------------------------------------------------------- #
#  Routes                                                                      #
# --------------------------------------------------------------------------- #
app.include_router(health.router, tags=["Health"])
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["Health"])
app.include_router(auth.router,         prefix=f"{settings.API_V1_STR}/auth",          tags=["Auth"])
app.include_router(trains.router,       prefix=f"{settings.API_V1_STR}/trains",        tags=["Trains"])
app.include_router(disruptions.router,  prefix=f"{settings.API_V1_STR}/disruptions",   tags=["Disruptions"])
app.include_router(cascade.router,      prefix=f"{settings.API_V1_STR}/cascade",       tags=["Cascade"])
app.include_router(rerouting.router,    prefix=f"{settings.API_V1_STR}/rerouting",     tags=["Rerouting"])
app.include_router(rac.router,          prefix=f"{settings.API_V1_STR}/rac",           tags=["RAC Predictor"])
app.include_router(audit.router,        prefix=f"{settings.API_V1_STR}/audit",         tags=["Audit"])
app.include_router(recommendations.router, prefix=f"{settings.API_V1_STR}/recommendations", tags=["Recommendations"])
app.include_router(stream.router,          prefix=f"{settings.API_V1_STR}/stream",          tags=["Stream SSE"])


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
