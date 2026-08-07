from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AuditLogEntry(BaseModel):
    id: Optional[str] = None
    agent_name: str
    action_type: (
        str  # 'MONITOR', 'CONFLICT_DETECTED', 'RECOMMENDATION_ISSUED', 'AUTO_ACTION', 'ESCALATION'
    )
    target: str  # Train no or station/section ID
    reasoning: str
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    prev_hash: str
    current_hash: str
    hash: Optional[str] = None


class AuditEntry(BaseModel):
    id: Optional[str] = None
    agent: str
    action: str
    target: str
    reasoning: str
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    hash: str
    prev_hash: str


class AuditVerification(BaseModel):
    chain_valid: bool
    last_verified: datetime
    total_records: int
    corrupted_records: List[str] = []
    genesis_valid: Optional[bool] = True
    links_valid: Optional[bool] = True
    signatures_valid: Optional[bool] = True
    timestamps_valid: Optional[bool] = True
    payloads_valid: Optional[bool] = True
