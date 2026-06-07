import hashlib
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.database import get_db, DBAuditEntry
from app.core.scenario_engine import scenario_engine
from app.models.audit import AuditLogEntry, AuditVerification

router = APIRouter()

# Helper to verify a single record hash self-consistency
def calculate_content_hash(entry: DBAuditEntry) -> str:
    # Deterministic payload based on content fields
    payload = f"{entry.agent_name}|{entry.action_type}|{entry.target}|{entry.reasoning}|{entry.confidence:.2f}|{entry.prev_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@router.get("/", response_model=List[AuditLogEntry])
async def list_audit_logs(db: AsyncSession = Depends(get_db)):
    # Order by ID asc to read chronological chain
    result = await db.execute(select(DBAuditEntry).order_by(DBAuditEntry.id.asc()))
    db_entries = result.scalars().all()
    
    if not db_entries and settings.SCENARIO_MODE:
        # Fallback to current memory logs if database has not been advanced/synced yet
        state = scenario_engine.get_state()
        result_entries = []
        prev_h = "0000000000000000000000000000000000000000000000000000000000000000"
        for idx, a in enumerate(state["audit_entries"]):
            result_entries.append(
                AuditLogEntry(
                    id=str(idx + 1),
                    agent_name=a["agent"],
                    action_type=a["action"],
                    target=a["target"],
                    reasoning=a["reasoning"],
                    confidence=a["confidence"],
                    timestamp=datetime.utcnow(),
                    prev_hash=prev_h,
                    current_hash=a["hash"]
                )
            )
            prev_h = a["hash"]
        return result_entries
        
    return [
        AuditLogEntry(
            id=str(e.id),
            agent_name=e.agent_name,
            action_type=e.action_type,
            target=e.target,
            reasoning=e.reasoning,
            confidence=e.confidence,
            timestamp=e.timestamp,
            prev_hash=e.prev_hash,
            current_hash=e.current_hash
        )
        for e in db_entries
    ]


@router.get("/verify", response_model=AuditVerification)
async def verify_audit_chain(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DBAuditEntry).order_by(DBAuditEntry.id.asc()))
    db_entries = result.scalars().all()
    
    # If no entries, it's verified (empty chain)
    if not db_entries:
        return AuditVerification(
            chain_valid=True,
            last_verified=datetime.utcnow(),
            total_records=0,
            corrupted_records=[]
        )
        
    corrupted = []
    
    # 1. Verify genesis block prev_hash
    genesis_expected = "0000000000000000000000000000000000000000000000000000000000000000"
    if db_entries[0].prev_hash != genesis_expected:
        corrupted.append(str(db_entries[0].id))
        
    # 2. Verify all link structures (prev_hash[i] == current_hash[i-1])
    for i in range(1, len(db_entries)):
        current = db_entries[i]
        previous = db_entries[i-1]
        
        if current.prev_hash != previous.current_hash:
            corrupted.append(str(current.id))
            
    chain_valid = len(corrupted) == 0
    
    return AuditVerification(
        chain_valid=chain_valid,
        last_verified=datetime.utcnow(),
        total_records=len(db_entries),
        corrupted_records=corrupted
    )
