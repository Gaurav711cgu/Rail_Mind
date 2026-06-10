import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "RailMind"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # ------------------------------------------------------------------ #
    #  Security — NEVER hardcode. All loaded from .env / HF Space secrets #
    # ------------------------------------------------------------------ #
    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY",
        "change-me-before-any-deployment-this-is-not-safe"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30          # 30 min access token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENFORCE_RBAC: bool = True                       # ALWAYS on

    # ------------------------------------------------------------------ #
    #  Hosts / CORS — never wildcard in production                        #
    # ------------------------------------------------------------------ #
    ALLOWED_HOSTS: List[str] = ["*"]               # Overridden by .env
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://railmind.vercel.app",             # Set real Vercel URL in .env
    ]

    # ------------------------------------------------------------------ #
    #  PostgreSQL (Supabase)                                               #
    #  Format: postgresql+asyncpg://USER:PASS@HOST:PORT/DB                #
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:password@localhost:5432/railmind"
    )
    # SQLite fallback used ONLY in test environments — never set in prod
    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///./test_railmind.db"

    # ------------------------------------------------------------------ #
    #  Redis (Upstash or local)                                            #
    #  Upstash format: rediss://default:TOKEN@HOST:PORT                   #
    # ------------------------------------------------------------------ #
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_STREAM_POSITIONS: str = "railmind:stream:positions"
    REDIS_STREAM_DISRUPTIONS: str = "railmind:stream:disruptions"
    REDIS_STREAM_RECOMMENDATIONS: str = "railmind:stream:recommendations"
    REDIS_STREAM_AUDIT: str = "railmind:stream:audit"
    REDIS_CACHE_TTL_POSITIONS: int = 90            # seconds
    REDIS_CACHE_TTL_GRAPH: int = 86400             # 24 hours

    # ------------------------------------------------------------------ #
    #  Anthropic (Dispatch Agent LLM)                                     #
    # ------------------------------------------------------------------ #
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # ------------------------------------------------------------------ #
    #  Live Data — indianrailapi.com / RapidAPI IRCTC                     #
    # ------------------------------------------------------------------ #
    LIVE_DATA_PROVIDER: str = "rapidapi-irctc"
    LIVE_TRAIN_WATCHLIST: str = "19038,12936,12002,22415"
    REAL_DATA_REQUIRED: bool = False
    RAPIDAPI_IRCTC_BASE_URL: str = "https://irctc1.p.rapidapi.com"
    RAPIDAPI_IRCTC_HOST: str = "irctc1.p.rapidapi.com"
    RAPIDAPI_IRCTC_KEY: str = ""
    RAPIDAPI_IRCTC_TIMEOUT_SECONDS: float = 10.0

    # ------------------------------------------------------------------ #
    #  ML Model paths                                                      #
    # ------------------------------------------------------------------ #
    RAC_MODEL_PATH: str = "app/ml/artifacts/rac_model.joblib"
    RAC_PIPELINE_PATH: str = "app/ml/artifacts/feature_pipeline.joblib"

    # ------------------------------------------------------------------ #
    #  Agent settings                                                      #
    # ------------------------------------------------------------------ #
    AGENT_DISPATCH_CONFIDENCE_THRESHOLD: float = 0.85
    AGENT_MONITOR_POLL_INTERVAL_SEC: int = 60
    AGENT_HEARTBEAT_INTERVAL_SEC: int = 30

    # ------------------------------------------------------------------ #
    #  Hackathon scenario engine (rich demo mode)                         #
    # ------------------------------------------------------------------ #
    SCENARIO_MODE: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
