from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    id: Optional[str] = None
    username: str
    email: EmailStr
    role: str  # 'PASSENGER', 'STATION_AGENT', 'CONTROLLER', 'ADMIN'
    zone: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    zone: Optional[str] = None
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
