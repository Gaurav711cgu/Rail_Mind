from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Station(BaseModel):
    code: str = Field(..., description="Unique IRCTC station code, e.g. NDLS")
    name: str
    zone: str
    division: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_major_junction: bool = False
    platform_count: Optional[int] = None


class Section(BaseModel):
    id: Optional[str] = None
    from_station: str
    to_station: str
    distance_km: float
    max_speed_kmh: int
    signaling_type: str = "ABSOLUTE_BLOCK"  # 'ABSOLUTE_BLOCK', 'ABS', 'EI', 'KAVACH'
    capacity_trains_per_hour: int = 10


class TrainPosition(BaseModel):
    train_no: str
    train_name: str
    at_station: str
    scheduled_arrival: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    delay_minutes: int = 0
    data_source: str = "indianrailapi"  # or 'ntes', 'cache'
    data_quality: float = 1.0  # 0.0 to 1.0
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


class TrainRouteNode(BaseModel):
    station_code: str
    station_name: str
    scheduled_arrival: Optional[str] = None      # HH:MM
    scheduled_departure: Optional[str] = None    # HH:MM
    actual_arrival: Optional[str] = None         # HH:MM
    actual_departure: Optional[str] = None       # HH:MM
    delay_arrival: int = 0
    delay_departure: int = 0
    status: str = "SCHEDULED"                     # 'SCHEDULED', 'ARRIVED', 'DEPARTED', 'SKIPPED'


class TrainStatus(BaseModel):
    train_no: str
    train_name: str
    current_station: str
    current_delay: int
    last_updated: datetime
    route: List[TrainRouteNode] = []
