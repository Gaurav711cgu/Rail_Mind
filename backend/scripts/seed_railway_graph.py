import asyncio
import sys
import os

# Append project root to sys.path to allow imports from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import init_db, AsyncSessionLocal, DBStation, DBSection, DBUser
from app.api.v1.routes.auth import get_password_hash
from sqlalchemy import delete

async def seed_data():
    print("Initializing database tables...")
    await init_db()
    
    async with AsyncSessionLocal() as session:
        # Clear existing tables to ensure clean seed
        print("Clearing existing railway topology...")
        await session.execute(delete(DBStation))
        await session.execute(delete(DBSection))
        await session.execute(delete(DBUser))
        
        print("Adding stations...")
        stations = [
            DBStation(code="NDLS", name="New Delhi", zone="NR", division="DLI", latitude=28.643, longitude=77.222, is_major_junction=True, platform_count=16),
            DBStation(code="GZB", name="Ghaziabad", zone="NR", division="DLI", latitude=28.672, longitude=77.436, is_major_junction=True, platform_count=6),
            DBStation(code="ALJN", name="Aligarh", zone="NR", division="DLI", latitude=27.892, longitude=78.078, is_major_junction=True, platform_count=7),
            DBStation(code="CNB", name="Kanpur Central", zone="NCR", division="PRYJ", latitude=26.454, longitude=80.350, is_major_junction=True, platform_count=10),
            DBStation(code="PRYJ", name="Prayagraj Jn", zone="NCR", division="PRYJ", latitude=25.448, longitude=81.851, is_major_junction=True, platform_count=12),
            DBStation(code="BSB", name="Varanasi", zone="NR", division="LKO", latitude=25.317, longitude=82.973, is_major_junction=True, platform_count=9)
        ]
        session.add_all(stations)
        
        print("Adding section segments...")
        sections = [
            DBSection(from_station="NDLS", to_station="GZB", distance_km=25.0, max_speed_kmh=110, signaling_type="ABSOLUTE_BLOCK", capacity_trains_per_hour=12),
            DBSection(from_station="GZB", to_station="ALJN", distance_km=100.0, max_speed_kmh=130, signaling_type="ABSOLUTE_BLOCK", capacity_trains_per_hour=10),
            DBSection(from_station="ALJN", to_station="CNB", distance_km=210.0, max_speed_kmh=130, signaling_type="ABSOLUTE_BLOCK", capacity_trains_per_hour=8),
            DBSection(from_station="CNB", to_station="PRYJ", distance_km=190.0, max_speed_kmh=130, signaling_type="KAVACH", capacity_trains_per_hour=15),
            DBSection(from_station="PRYJ", to_station="BSB", distance_km=120.0, max_speed_kmh=110, signaling_type="KAVACH", capacity_trains_per_hour=15)
        ]
        session.add_all(sections)
        
        print("Adding default accounts...")
        controller_pass = get_password_hash("controller123")
        users = [
            DBUser(username="controller_north", email="controller@railmind.gov.in", password_hash=controller_pass, role="CONTROLLER", zone="NR"),
            DBUser(username="admin", email="admin@railmind.gov.in", password_hash=get_password_hash("admin123"), role="ADMIN", zone="NR")
        ]
        session.add_all(users)
        
        await session.commit()
        print("Database seeding successfully completed!")

if __name__ == "__main__":
    asyncio.run(seed_data())
