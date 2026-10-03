"""
Redis-backed async cache with fallback in-memory store for development.
"""
import json
import time
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_redis_client: Optional[aioredis.Redis] = None
_memory_cache: dict = {}  # fallback


async def get_redis() -> Optional[aioredis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await _redis_client.ping()
            logger.info("redis_connected", url=settings.redis_url)
        except Exception as e:
            logger.warning("redis_unavailable", error=str(e), fallback="in-memory")
            _redis_client = None
    return _redis_client


async def cache_get(key: str) -> Optional[Any]:
    redis = await get_redis()
    try:
        if redis:
            value = await redis.get(key)
            if value:
                return json.loads(value)
        else:
            entry = _memory_cache.get(key)
            if entry and entry["expires"] > time.time():
                return entry["value"]
    except Exception as e:
        logger.warning("cache_get_error", key=key, error=str(e))
    return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    redis = await get_redis()
    try:
        serialized = json.dumps(value, default=str)
        if redis:
            await redis.setex(key, ttl, serialized)
        else:
            _memory_cache[key] = {
                "value": value,
                "expires": time.time() + ttl,
            }
    except Exception as e:
        logger.warning("cache_set_error", key=key, error=str(e))


async def cache_delete(key: str) -> None:
    redis = await get_redis()
    try:
        if redis:
            await redis.delete(key)
        else:
            _memory_cache.pop(key, None)
    except Exception as e:
        logger.warning("cache_delete_error", key=key, error=str(e))
