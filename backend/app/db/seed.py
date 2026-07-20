from sqlalchemy import select
from app.db.database import AsyncSessionLocal, DBStation, DBSection, DBUser
from app.api.v1.routes.auth import get_password_hash


async def seed_topology():
    """Seeds the database with the initial railway topology (stations, sections, users) if empty."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(DBStation).limit(1))
        if not result.scalars().first():
            print("[Lifespan] Seeding railway topology...")
            stations = [
                DBStation(
                    code="NDLS",
                    name="New Delhi",
                    zone="NR",
                    division="DLI",
                    latitude=28.643,
                    longitude=77.222,
                    is_major_junction=True,
                    platform_count=16,
                ),
                DBStation(
                    code="GZB",
                    name="Ghaziabad",
                    zone="NR",
                    division="DLI",
                    latitude=28.672,
                    longitude=77.436,
                    is_major_junction=True,
                    platform_count=6,
                ),
                DBStation(
                    code="ALJN",
                    name="Aligarh Jn",
                    zone="NR",
                    division="DLI",
                    latitude=27.892,
                    longitude=78.078,
                    is_major_junction=True,
                    platform_count=7,
                ),
                DBStation(
                    code="CNB",
                    name="Kanpur Central",
                    zone="NCR",
                    division="PRYJ",
                    latitude=26.454,
                    longitude=80.350,
                    is_major_junction=True,
                    platform_count=10,
                ),
                DBStation(
                    code="PRYJ",
                    name="Prayagraj Jn",
                    zone="NCR",
                    division="PRYJ",
                    latitude=25.448,
                    longitude=81.851,
                    is_major_junction=True,
                    platform_count=12,
                ),
                DBStation(
                    code="BSB",
                    name="Varanasi Jn",
                    zone="NR",
                    division="LKO",
                    latitude=25.317,
                    longitude=82.973,
                    is_major_junction=True,
                    platform_count=9,
                ),
                DBStation(
                    code="HWH",
                    name="Howrah Jn",
                    zone="ER",
                    division="HWH",
                    latitude=22.583,
                    longitude=88.342,
                    is_major_junction=True,
                    platform_count=23,
                ),
                DBStation(
                    code="MMCT",
                    name="Mumbai Central",
                    zone="WR",
                    division="BCT",
                    latitude=18.971,
                    longitude=72.820,
                    is_major_junction=True,
                    platform_count=8,
                ),
                DBStation(
                    code="BRC",
                    name="Vadodara Jn",
                    zone="WR",
                    division="BRC",
                    latitude=22.312,
                    longitude=73.181,
                    is_major_junction=True,
                    platform_count=6,
                ),
                DBStation(
                    code="MAS",
                    name="Chennai Central",
                    zone="SR",
                    division="MAS",
                    latitude=13.082,
                    longitude=80.275,
                    is_major_junction=True,
                    platform_count=17,
                ),
                DBStation(
                    code="SBC",
                    name="KSR Bengaluru",
                    zone="SWR",
                    division="SBC",
                    latitude=12.978,
                    longitude=77.572,
                    is_major_junction=True,
                    platform_count=10,
                ),
                DBStation(
                    code="SC",
                    name="Secunderabad Jn",
                    zone="SCR",
                    division="SC",
                    latitude=17.431,
                    longitude=78.501,
                    is_major_junction=True,
                    platform_count=10,
                ),
            ]
            session.add_all(stations)

            sections = [
                DBSection(
                    from_station="NDLS",
                    to_station="GZB",
                    distance_km=25,
                    max_speed_kmh=110,
                    signaling_type="ABSOLUTE_BLOCK",
                    capacity_trains_per_hour=12,
                ),
                DBSection(
                    from_station="GZB",
                    to_station="ALJN",
                    distance_km=100,
                    max_speed_kmh=130,
                    signaling_type="ABSOLUTE_BLOCK",
                    capacity_trains_per_hour=10,
                ),
                DBSection(
                    from_station="ALJN",
                    to_station="CNB",
                    distance_km=210,
                    max_speed_kmh=130,
                    signaling_type="ABSOLUTE_BLOCK",
                    capacity_trains_per_hour=8,
                ),
                DBSection(
                    from_station="CNB",
                    to_station="PRYJ",
                    distance_km=190,
                    max_speed_kmh=130,
                    signaling_type="KAVACH",
                    capacity_trains_per_hour=15,
                ),
                DBSection(
                    from_station="PRYJ",
                    to_station="BSB",
                    distance_km=120,
                    max_speed_kmh=110,
                    signaling_type="KAVACH",
                    capacity_trains_per_hour=15,
                ),
                DBSection(
                    from_station="BSB",
                    to_station="HWH",
                    distance_km=635,
                    max_speed_kmh=100,
                    signaling_type="ABSOLUTE_BLOCK",
                    capacity_trains_per_hour=8,
                ),
                DBSection(
                    from_station="NDLS",
                    to_station="MMCT",
                    distance_km=1384,
                    max_speed_kmh=130,
                    signaling_type="ABS",
                    capacity_trains_per_hour=10,
                ),
                DBSection(
                    from_station="BRC",
                    to_station="MMCT",
                    distance_km=391,
                    max_speed_kmh=130,
                    signaling_type="ABSOLUTE_BLOCK",
                    capacity_trains_per_hour=12,
                ),
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
