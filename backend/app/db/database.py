from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, event
from app.config import settings

def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Base class for ORM models
Base = declarative_base()

# Async database session configuration
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


# Dependency generator for routes
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ORM Model Definitions

class DBUser(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="PASSENGER")  # PASSENGER, CONTROLLER, ADMIN
    zone: Mapped[str] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


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
    trains_affected_json: Mapped[str] = mapped_column(Text, default="[]")  # Serialized list
    passengers_affected: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE, RESOLVED, ESCALATED
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class DBRecommendation(Base):
    __tablename__ = "recommendations"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    disruption_id: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="HOLD")  # HOLD, PROCEED, ESCALATE
    target_train: Mapped[str] = mapped_column(String(10), nullable=False)
    target_section: Mapped[str] = mapped_column(String(100), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[int] = mapped_column(Integer, default=1)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[str] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class DBAuditEntry(Base):
    __tablename__ = "audit_log"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target: Mapped[str] = mapped_column(String(100), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False)


# Initialize Database tables
async def init_db():
    async with engine.begin() as conn:
        # Create all tables if they do not exist
        await conn.run_sync(Base.metadata.create_all)


# --------------------------------------------------------------------------- #
#  Audit-log tamper-proofing                                                   #
#  Block UPDATE / DELETE on the audit_log table at the cursor level.           #
# --------------------------------------------------------------------------- #
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _guard_audit_log(conn, cursor, statement, parameters, context, executemany):
    """Raise PermissionError if a statement tries to UPDATE or DELETE audit_log rows."""
    normalised = statement.upper()
    if ("UPDATE" in normalised or "DELETE" in normalised) and "AUDIT_LOG" in normalised:
        raise PermissionError(
            "Audit log is append-only: UPDATE/DELETE operations are forbidden."
        )
