import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "RailMind"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "SUPER_SECRET_SECURITY_HASH_KEY_RAILMIND_2026_GRAND_FINALS"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days for hackathon development
    ENFORCE_RBAC: bool = False
    
    # Server / Hosts
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = ["*"]
    
    # Databases
    DATABASE_URL: str = "sqlite+aiosqlite:///./railmind_local.db"
    REDIS_URL: str = "redis://localhost:6379/0"  # Fallback for streams/caching
    
    # Railway Settings
    USD_INR_RATE: float = 83.5
    LIVE_DATA_PROVIDER: str = "rapidapi-irctc"
    LIVE_TRAIN_WATCHLIST: str = "19038,12936,12002,22415"
    REAL_DATA_REQUIRED: bool = False
    RAPIDAPI_IRCTC_BASE_URL: str = "https://irctc1.p.rapidapi.com"
    RAPIDAPI_IRCTC_HOST: str = "irctc1.p.rapidapi.com"
    RAPIDAPI_IRCTC_KEY: str = ""
    RAPIDAPI_IRCTC_TIMEOUT_SECONDS: float = 10.0
    
    # Hackathon Presentation Mode
    SCENARIO_MODE: bool = True  # Activates the high-fidelity mock engine
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


settings = Settings()
