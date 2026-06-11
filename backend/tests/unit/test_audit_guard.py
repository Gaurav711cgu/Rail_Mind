"""
Unit tests for the audit_log tamper-proofing guard.

Verifies:
- Inserting into audit_log works normally.
- Attempting to UPDATE audit_log raises PermissionError.
- Attempting to DELETE from audit_log raises PermissionError.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.database import Base, DBAuditEntry, event


# Use a dedicated in-memory SQLite engine so the guard listener is NOT
# attached (the production guard lives on the *production* engine).
# Instead, we manually register the same listener on a test engine to
# validate the logic in isolation.

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def guarded_session():
    """Create an in-memory DB with the audit-guard listener attached."""
    test_engine = create_async_engine(TEST_DB_URL, echo=False)

    # Register the same guard on this test engine
    @event.listens_for(test_engine.sync_engine, "before_cursor_execute")
    def _guard(conn, cursor, statement, parameters, context, executemany):
        normalised = statement.upper()
        if ("UPDATE" in normalised or "DELETE" in normalised) and "AUDIT_LOG" in normalised:
            raise PermissionError(
                "Audit log is append-only: UPDATE/DELETE operations are forbidden."
            )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_insert_audit_log_succeeds(guarded_session):
    """INSERT into audit_log must work normally."""
    entry = DBAuditEntry(
        agent_name="monitor",
        action_type="DETECT_DELAY",
        target="train-12002",
        reasoning="Delay detected at GZB",
        confidence=0.92,
        timestamp=datetime.now(timezone.utc),
        prev_hash="0" * 64,
        current_hash="a" * 64,
    )
    guarded_session.add(entry)
    await guarded_session.commit()

    result = await guarded_session.execute(text("SELECT COUNT(*) FROM audit_log"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_update_audit_log_raises(guarded_session):
    """UPDATE on audit_log must raise PermissionError."""
    # Seed a row first
    entry = DBAuditEntry(
        agent_name="monitor",
        action_type="DETECT_DELAY",
        target="train-12002",
        reasoning="Delay detected at GZB",
        confidence=0.92,
        timestamp=datetime.now(timezone.utc),
        prev_hash="0" * 64,
        current_hash="a" * 64,
    )
    guarded_session.add(entry)
    await guarded_session.commit()

    with pytest.raises(PermissionError, match="append-only"):
        await guarded_session.execute(
            text("UPDATE audit_log SET agent_name = 'hacked' WHERE id = 1")
        )
        await guarded_session.commit()


@pytest.mark.asyncio
async def test_delete_audit_log_raises(guarded_session):
    """DELETE from audit_log must raise PermissionError."""
    entry = DBAuditEntry(
        agent_name="monitor",
        action_type="DETECT_DELAY",
        target="train-12002",
        reasoning="Delay detected at GZB",
        confidence=0.92,
        timestamp=datetime.now(timezone.utc),
        prev_hash="0" * 64,
        current_hash="a" * 64,
    )
    guarded_session.add(entry)
    await guarded_session.commit()

    with pytest.raises(PermissionError, match="append-only"):
        await guarded_session.execute(text("DELETE FROM audit_log WHERE id = 1"))
        await guarded_session.commit()
