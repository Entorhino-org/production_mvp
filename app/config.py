"""
Application configuration — loads infrastructure settings from .env file.
All AI/service settings (API keys, models, voices) are managed in System Config (DB).
"""

from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import PrivateAttr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_postgres_url_for_asyncpg(url: str) -> tuple[str, str | None]:
    """
    - postgresql:// / postgres:// → postgresql+asyncpg:// (psycopg2 is not installed).
    - ?schema=mvp (common in Azure samples) is not a libpq parameter: strip it and
      return the schema name so the engine can set search_path (mvp, public).
    """
    s = url.strip()
    if s.startswith("postgres://"):
        s = "postgresql://" + s[len("postgres://") :]

    parsed = urlparse(s)
    qsl = parse_qsl(parsed.query, keep_blank_values=True)
    schema_from_query: str | None = None
    rest: list[tuple[str, str]] = []
    for k, v in qsl:
        if k.lower() == "schema":
            schema_from_query = v.strip() if v else None
        else:
            rest.append((k, v))
    new_query = urlencode(rest) if rest else ""

    sl = parsed.scheme.lower()
    if sl in ("postgresql", "postgres"):
        scheme = "postgresql+asyncpg"
    elif sl == "postgresql+asyncpg":
        scheme = "postgresql+asyncpg"
    else:
        scheme = parsed.scheme
    new_parsed = parsed._replace(scheme=scheme, query=new_query)
    return urlunparse(new_parsed), schema_from_query


class Settings(BaseSettings):
    """Infrastructure configuration loaded from environment variables."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    ) # this for line of code mein setting class ko .env file se load karne ke liye use kiya jata hai
    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://entorhino:entorhino@localhost:5432/entorhino"

    _asyncpg_search_path: str | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _apply_database_url_normalization(self):
        clean, schema = normalize_postgres_url_for_asyncpg(self.DATABASE_URL)
        object.__setattr__(self, "DATABASE_URL", clean)
        self._asyncpg_search_path = f"{schema},public" if schema else None
        return self

    @property
    def asyncpg_connect_server_settings(self) -> dict[str, str] | None:
        """Passed to create_async_engine(connect_args) when ?schema= was used."""
        if self._asyncpg_search_path:
            return {"search_path": self._asyncpg_search_path}
        return None

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


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — call this wherever config is needed."""
    return Settings()
