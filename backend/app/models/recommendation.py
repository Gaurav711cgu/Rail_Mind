from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DispatchRec(BaseModel):
    id: Optional[str] = None
    disruption_id: str
    type: str = "HOLD"  # 'HOLD', 'PROCEED', 'REROUTE_FREIGHT', 'ESCALATE'
    target_train: str
    target_section: str
    reasoning: str
    confidence: float
    tier: int = 1  # 1 = Auto, 2 = Manual Escalated
    is_approved: bool = False
    override_reason: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class AlternativeTrain(BaseModel):
    train_no: str
    departure_station: str
    departure_time: str
    arrival_time: str
    seat_availability: str
    rac_confirmation_probability: float
    connection_required: bool = False


class ReroutingSuggestion(BaseModel):
    id: Optional[str] = None
    disruption_id: str
    passenger_origin: str
    passenger_destination: str
    alternatives: List[AlternativeTrain] = []
    advisory_text: str
    generated_by_agent: str = "NotificationAgent"
    confidence: float = 0.90
    generated_at: datetime = Field(default_factory=datetime.utcnow)
