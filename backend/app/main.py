from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.db.database import init_db, AsyncSessionLocal, DBStation, DBSection, DBUser
from app.api.v1.routes import auth, trains, disruptions, cascade, rerouting, rac, audit, health
from app.api.v1.routes.auth import get_password_hash

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize DB tables
    print("[Lifespan] Initializing database schemas...")
    await init_db()
    
    # 2. Seed database topology
    async with AsyncSessionLocal() as session:
        # Check if stations exist
        result = await session.execute(select(DBStation).limit(1))
        if not result.scalars().first():
            print("[Lifespan] Seeding railway topology nodes...")
            stations = [
                DBStation(code="NDLS", name="New Delhi", zone="NR", division="DLI", latitude=28.643, longitude=77.222, is_major_junction=True, platform_count=16),
                DBStation(code="GZB", name="Ghaziabad", zone="NR", division="DLI", latitude=28.672, longitude=77.436, is_major_junction=True, platform_count=6),
                DBStation(code="ALJN", name="Aligarh", zone="NR", division="DLI", latitude=27.892, longitude=78.078, is_major_junction=True, platform_count=7),
                DBStation(code="CNB", name="Kanpur Central", zone="NCR", division="PRYJ", latitude=26.454, longitude=80.350, is_major_junction=True, platform_count=10),
                DBStation(code="PRYJ", name="Prayagraj Jn", zone="NCR", division="PRYJ", latitude=25.448, longitude=81.851, is_major_junction=True, platform_count=12),
                DBStation(code="BSB", name="Varanasi", zone="NR", division="LKO", latitude=25.317, longitude=82.973, is_major_junction=True, platform_count=9)
            ]
            session.add_all(stations)
            
            sections = [
                DBSection(from_station="NDLS", to_station="GZB", distance_km=25.0, max_speed_kmh=110, signaling_type="ABSOLUTE_BLOCK", capacity_trains_per_hour=12),
                DBSection(from_station="GZB", to_station="ALJN", distance_km=100.0, max_speed_kmh=130, signaling_type="ABSOLUTE_BLOCK", capacity_trains_per_hour=10),
                DBSection(from_station="ALJN", to_station="CNB", distance_km=210.0, max_speed_kmh=130, signaling_type="ABSOLUTE_BLOCK", capacity_trains_per_hour=8),
                DBSection(from_station="CNB", to_station="PRYJ", distance_km=190.0, max_speed_kmh=130, signaling_type="KAVACH", capacity_trains_per_hour=15),
                DBSection(from_station="PRYJ", to_station="BSB", distance_km=120.0, max_speed_kmh=110, signaling_type="KAVACH", capacity_trains_per_hour=15)
            ]
            session.add_all(sections)
            
            # Seed default system users
            print("[Lifespan] Seeding default operator and controller accounts...")
            controller_pass = get_password_hash("controller123")
            users = [
                DBUser(username="controller_north", email="controller@railmind.gov.in", password_hash=controller_pass, role="CONTROLLER", zone="NR"),
                DBUser(username="admin", email="admin@railmind.gov.in", password_hash=get_password_hash("admin123"), role="ADMIN", zone="NR")
            ]
            session.add_all(users)
            
            await session.commit()
            print("[Lifespan] Database seeding completed successfully.")
        else:
            print("[Lifespan] Railway topology nodes already present. Skipping seed.")
            
    yield
    print("[Lifespan] Shutting down backend engine...")


# App instantiation
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous Agentic Dispatching & Punctuality Engine for Indian Railways",
    lifespan=lifespan
)

# CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes
app.include_router(health.router, tags=["Health Checks"])
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["Health Checks"])
app.include_router(auth.router, prefix=settings.API_V1_STR + "/auth", tags=["Authentication"])
app.include_router(trains.router, prefix=settings.API_V1_STR + "/trains", tags=["Train Tracking"])
app.include_router(disruptions.router, prefix=settings.API_V1_STR + "/disruptions", tags=["Disruptions Registry"])
app.include_router(cascade.router, prefix=settings.API_V1_STR + "/cascade", tags=["Cascade Predictor Engine"])
app.include_router(rerouting.router, prefix=settings.API_V1_STR + "/rerouting", tags=["Rerouting Advisories"])
app.include_router(rac.router, prefix=settings.API_V1_STR + "/rac", tags=["RAC Confirmation Predictor"])
app.include_router(audit.router, prefix=settings.API_V1_STR + "/audit", tags=["Cryptographic Decision Log"])


@app.get("/")
async def root():
    return {
        "message": "Welcome to the RailMind Engine API",
        "docs_url": "/docs",
        "health": "/health",
        "scenario_mode": settings.SCENARIO_MODE
    }
