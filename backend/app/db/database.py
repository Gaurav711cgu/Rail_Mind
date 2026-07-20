from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, event, DDL, CheckConstraint
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings


class Base(DeclarativeBase):
    pass


# ------------------------------------------------------------------ #
#  Engine — asyncpg for PostgreSQL, aiosqlite fallback for tests      #
# ------------------------------------------------------------------ #
def _make_engine(url: str):
    is_sqlite = url.startswith("sqlite")
    return create_async_engine(
        url,
        echo=False,
        pool_pre_ping=True,  # detect stale connections
        **(
            {}
            if is_sqlite
            else {
                "pool_size": 10,
                "max_overflow": 20,
                "pool_timeout": 30,
            }
        ),
    )


engine = _make_engine(settings.DATABASE_URL)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ------------------------------------------------------------------ #
#  ORM Models                                                          #
# ------------------------------------------------------------------ #


class DBUser(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50),
        default="PASSENGER",
        # Valid roles enforced at DB level
    )
    zone: Mapped[str] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "role IN ('PASSENGER','STATION_AGENT','CONTROLLER','ADMIN')",
            name="ck_users_role",
        ),
    )


class DBStation(Base):
    __tablename__ = "stations"

    code: Mapped[str] = mapped_column(String(10), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    zone: Mapped[str] = mapped_column(String(10), nullable=False)
    division: Mapped[str] = mapped_column(String(50), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    is_major_junction: Mapped[bool] = mapped_column(Boolean, default=False)
    platform_count: Mapped[int] = mapped_column(Integer, nullable=True)


class DBSection(Base):
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    from_station: Mapped[str] = mapped_column(String(10), nullable=False)
    to_station: Mapped[str] = mapped_column(String(10), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    max_speed_kmh: Mapped[int] = mapped_column(Integer, default=110)
    signaling_type: Mapped[str] = mapped_column(String(50), default="ABSOLUTE_BLOCK")
    capacity_trains_per_hour: Mapped[int] = mapped_column(Integer, default=10)


class DBDisruption(Base):
    __tablename__ = "disruptions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    train_no: Mapped[str] = mapped_column(String(10), nullable=False)
    section_from: Mapped[str] = mapped_column(String(10), nullable=False)
    section_to: Mapped[str] = mapped_column(String(10), nullable=False)
    disruption_type: Mapped[str] = mapped_column(String(50), default="DELAY_CASCADE")
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    cascade_depth: Mapped[int] = mapped_column(Integer, default=0)
    trains_affected_json: Mapped[str] = mapped_column(Text, default="[]")
    passengers_affected: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "severity IN ('LOW','MEDIUM','HIGH','CRITICAL')",
            name="ck_disruptions_severity",
        ),
        CheckConstraint(
            "status IN ('ACTIVE','RESOLVED','ESCALATED')",
            name="ck_disruptions_status",
        ),
    )


class DBRecommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    disruption_id: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="HOLD")
    target_train: Mapped[str] = mapped_column(String(10), nullable=False)
    target_section: Mapped[str] = mapped_column(String(100), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[int] = mapped_column(Integer, default=1)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[str] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DBAuditEntry(Base):
    """
    APPEND-ONLY table.
    Enforcement layers:
      1. CheckConstraint prevents NULL hashes
      2. SQLAlchemy never exposes UPDATE/DELETE on this model
      3. PostgreSQL row-level security (applied via DDL below after table creation)
      4. Separate INSERT-only DB role in production Supabase setup
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target: Mapped[str] = mapped_column(String(200), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    __table_args__ = (
        CheckConstraint("length(current_hash) = 64", name="ck_audit_hash_length"),
        CheckConstraint("length(prev_hash) = 64", name="ck_audit_prev_hash_length"),
    )


class DBOutboxEvent(Base):
    """
    Transactional Outbox pattern for safe agent execution.
    Agent decisions that alter physical/external state are written here within the same DB transaction.
    A separate background worker polls this table and publishes to Redis/Kafka.
    """
    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True) # PENDING, PROCESSED, FAILED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)



# ------------------------------------------------------------------ #
#  PostgreSQL-only DDL: RLS append-only policy on audit_log           #
#  (Skipped for SQLite test environments)                             #
# ------------------------------------------------------------------ #
_AUDIT_RLS_DDL = DDL("""
    ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE tablename = 'audit_log' AND policyname = 'audit_insert_only'
        ) THEN
            CREATE POLICY audit_insert_only ON audit_log FOR INSERT WITH CHECK (true);
        END IF;
    END
    $$;
""")

event.listen(
    DBAuditEntry.__table__,
    "after_create",
    _AUDIT_RLS_DDL.execute_if(dialect="postgresql"),
)


# ------------------------------------------------------------------ #
#  TimescaleDB hypertable for train_positions (applied post-create)   #
# ------------------------------------------------------------------ #
class DBTrainPosition(Base):
    """
    Time-series table. On PostgreSQL + TimescaleDB, converted to a
    hypertable via the DDL listener below.
    """

    __tablename__ = "train_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    train_no: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    train_name: Mapped[str] = mapped_column(String(255), nullable=True)
    at_station: Mapped[str] = mapped_column(String(10), nullable=True)
    scheduled_arrival: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    actual_arrival: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    delay_minutes: Mapped[int] = mapped_column(Integer, default=0)
    data_source: Mapped[str] = mapped_column(String(50), default="indianrailapi")
    data_quality: Mapped[float] = mapped_column(Float, default=1.0)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True, nullable=False
    )


_TIMESCALE_DDL = DDL("""
    SELECT create_hypertable(
        'train_positions', 'recorded_at',
        if_not_exists => TRUE,
        migrate_data   => TRUE
    );
""")

event.listen(
    DBTrainPosition.__table__,
    "after_create",
    _TIMESCALE_DDL.execute_if(dialect="postgresql"),
)


# ------------------------------------------------------------------ #
#  Live Mode / Telemetry Cache Models                                  #
# ------------------------------------------------------------------ #
class DBTrainTelemetryCache(Base):
    __tablename__ = "train_telemetry_cache"

    train_no: Mapped[str] = mapped_column(String(10), primary_key=True, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DBLiveAgentRun(Base):
    __tablename__ = "live_agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")
    metrics_json: Mapped[str] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


# ------------------------------------------------------------------ #
#  Init                                                                #
# ------------------------------------------------------------------ #
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
