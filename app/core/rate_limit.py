"""
Redis-backed rate limiter with in-memory fallback.
Uses Redis INCR + EXPIRE for atomic sliding-window rate limiting.
Falls back to the original in-memory implementation if Redis is unavailable.
"""

import time
import logging
import threading
from collections import defaultdict
from fastapi import HTTPException, Request

from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class _InMemoryLimiter:
    """Fallback in-memory sliding-window rate limiter."""

    def __init__(self):
        self._store: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str, max_requests: int, window_seconds: int):
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            self._store[key] = [t for t in self._store[key] if t > cutoff]
            if len(self._store[key]) >= max_requests:
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many requests. Try again in {window_seconds} seconds.",
                )
            self._store[key].append(now)

    def cleanup(self, max_age: int = 300):
        now = time.time()
        cutoff = now - max_age
        with self._lock:
            empty_keys = []
            for key, timestamps in self._store.items():
                self._store[key] = [t for t in timestamps if t > cutoff]
                if not self._store[key]:
                    empty_keys.append(key)
            for key in empty_keys:
                del self._store[key]


_fallback = _InMemoryLimiter()


class RateLimiter:
    """Redis-backed rate limiter with automatic in-memory fallback."""

    async def check_async(self, key: str, max_requests: int, window_seconds: int):
        """Async check using Redis. Falls back to in-memory if Redis unavailable."""
        r = get_redis()
        if r is None:
            # Fallback to in-memory
            _fallback.check(key, max_requests, window_seconds)
            return

        redis_key = f"rl:{key}"
        try:
            current = await r.incr(redis_key)
            if current == 1:
                await r.expire(redis_key, window_seconds)
            if current > max_requests:
                ttl = await r.ttl(redis_key)
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many requests. Try again in {ttl if ttl > 0 else window_seconds} seconds.",
                )
        except HTTPException:
            raise
        except Exception:
            # Redis error — fall back to in-memory
            _fallback.check(key, max_requests, window_seconds)

    def check(self, key: str, max_requests: int, window_seconds: int):
        """Sync check — always uses in-memory (for backwards compat in sync contexts)."""
        _fallback.check(key, max_requests, window_seconds)


# Global instance
limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
