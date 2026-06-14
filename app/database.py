"""
Async SQLAlchemy engine, session factory, and declarative base.
Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite) for local dev.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {
    "echo": False,
    "pool_pre_ping": True,
}

if _is_sqlite:
    # SQLite doesn't support pool_size/max_overflow; use StaticPool for async
    from sqlalchemy.pool import StaticPool
    _engine_kwargs["poolclass"] = StaticPool
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_size"] = 50
    _engine_kwargs["max_overflow"] = 20
    _connect_args: dict = {}
    if settings.asyncpg_connect_server_settings:
        _connect_args["server_settings"] = settings.asyncpg_connect_server_settings
    if _connect_args:
        _engine_kwargs["connect_args"] = _connect_args

# Async engine — pool sized for ~5k users / multi-school
engine = create_async_engine(
    settings.DATABASE_URL,
    **_engine_kwargs,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
