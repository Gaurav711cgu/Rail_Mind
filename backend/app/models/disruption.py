from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Disruption(BaseModel):
    id: Optional[str] = None
    train_no: str
    section_from: str
    section_to: str
    disruption_type: str = (
        "DELAY_CASCADE"  # 'DELAY_CASCADE', 'SIGNAL_FAILURE', 'TRACK_FAULT', 'WEATHER'
    )
    severity: str = "MEDIUM"  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    cascade_depth: int = 0
    trains_affected: List[str] = []
    passengers_affected: int = 0
    status: str = "ACTIVE"  # 'ACTIVE', 'RESOLVED', 'ESCALATED'
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None


class CascadeEvent(BaseModel):
    train_no: str
    station: str
    delay_added_minutes: int
    confidence: float


class CascadeReport(BaseModel):
    root_disruption_id: str
    cascade_depth: int
    affected_trains: List[CascadeEvent] = []
    total_passengers_affected: int = 0
    weather_factor: float = 1.0
    agent_confidence: float = 0.95
    reasoning: str
