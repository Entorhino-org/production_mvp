"""
Async Redis client singleton.
Provides get_redis() for use as a FastAPI dependency or direct import.
Gracefully falls back to None if Redis is unavailable.
"""

import logging
from typing import Optional

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> Optional[aioredis.Redis]:
    """Initialize the global Redis connection. Called on app startup."""
    global _redis_client
    settings = get_settings()
    try:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        await _redis_client.ping()
        logger.info("✅ Redis connected at %s", settings.REDIS_URL)
        return _redis_client
    except Exception as e:
        logger.warning("⚠️ Redis unavailable (%s) — falling back to in-memory", e)
        _redis_client = None
        return None


async def close_redis():
    """Close the Redis connection. Called on app shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")


def get_redis() -> Optional[aioredis.Redis]:
    """Get the Redis client. Returns None if Redis is not available."""
    return _redis_client
