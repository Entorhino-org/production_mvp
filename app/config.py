"""
Application configuration — loads infrastructure settings from .env file.
All AI/service settings (API keys, models, voices) are managed in System Config (DB).
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Infrastructure configuration loaded from environment variables."""

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://entorhino:entorhino@localhost:5432/entorhino"

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── OpenRouter (bootstrap — override in System Config) ───
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "google/gemini-2.0-flash-001"

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Uploads ──────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # ── Web Push (VAPID) ─────────────────────────────────────
    VAPID_PRIVATE_KEY: str = "QpdVHElCvGTP9O0nzq-t2PVahTDYyGSpmYMPKDAQbL0"
    VAPID_PUBLIC_KEY: str = "BGVDZ44umnm9av3IIUOVEQNZ7-Scc8vDmLxrwgVgKlY00s3Us5PVTIimslkpq9a7lp_yX6YO1_t2aAjHyNJSJqw"
    VAPID_MAILTO: str = "mailto:infra@entorhino.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — call this wherever config is needed."""
    return Settings()
