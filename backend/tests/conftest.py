"""
conftest.py — shared pytest fixtures for RailMind test suite.

Test database: SQLite in-memory (aiosqlite) — no Postgres required locally.
Redis: uses the in-memory fallback in stream_service.py automatically.
LLM: Anthropic calls are monkeypatched so no API key is needed in CI.
"""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.db.database import Base, get_db
from app.config import settings

# Force test DB settings before anything imports them
settings.DATABASE_URL = "sqlite+aiosqlite:///./test_railmind.db"
settings.REDIS_URL = "redis://localhost:6379/0"    # falls back to in-memory if not running
settings.SCENARIO_MODE = True
settings.ENFORCE_RBAC = True
settings.ANTHROPIC_API_KEY = ""                    # LLM disabled in tests

TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///./test_railmind.db",
    echo=False,
)
TestSessionLocal = async_sessionmaker(
    bind=TEST_ENGINE,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create all tables once per session, drop after."""
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await TEST_ENGINE.dispose()


@pytest_asyncio.fixture
async def db_session():
    """Yields a fresh DB session, rolled back after each test."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """Async HTTP client wired to the FastAPI app with the test DB."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
#  Shared test data factories                                                  #
# --------------------------------------------------------------------------- #

def make_train(
    train_no: str = "12002",
    delay: int = 45,
    station: str = "GZB",
    status: str = "DELAYED",
    train_type: str = "SUPERFAST",
) -> dict:
    return {
        "train_no": train_no,
        "train_name": f"Test Train {train_no}",
        "current_station": station,
        "current_delay": delay,
        "status": status,
        "train_type": train_type,
        "data_quality": 1.0,
        "data_source": "test",
    }


def make_disruption(
    train_no: str = "12002",
    section_from: str = "GZB",
    section_to: str = "ALJN",
    severity: str = "HIGH",
    disp_type: str = "DELAY_CASCADE",
) -> dict:
    return {
        "id": f"disp-test-{train_no}",
        "train_no": train_no,
        "section_from": section_from,
        "section_to": section_to,
        "disruption_type": disp_type,
        "severity": severity,
        "cascade_depth": 0,
        "status": "ACTIVE",
        "upstream_delay_minutes": 45,
    }
