from functools import lru_cache

import redis.asyncio as redis
from redis.exceptions import ConnectionError, RedisError

from app.core.config import get_settings

_redis: redis.Redis | None = None


def is_redis_available() -> bool:
    settings = get_settings()
    return bool(settings.redis_enabled and settings.redis_url and get_redis() is not None)


@lru_cache
def get_redis() -> redis.Redis | None:
    global _redis
    settings = get_settings()
    if not settings.redis_enabled or not settings.redis_url:
        return None
    try:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
        return _redis
    except Exception:
        return None


async def cache_get(key: str) -> str | None:
    client = get_redis()
    if client is None:
        return None
    try:
        return await client.get(key)
    except (ConnectionError, RedisError, OSError):
        return None


async def cache_setex(key: str, ttl_seconds: int, value: str) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        await client.setex(key, ttl_seconds, value)
    except (ConnectionError, RedisError, OSError):
        return


async def invalidate_map_cache() -> None:
    client = get_redis()
    if client is None:
        return
    try:
        async for key in client.scan_iter("map:*"):
            await client.delete(key)
    except (ConnectionError, RedisError, OSError):
        return


async def invalidate_photo_cache(photo_id: str) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        await client.delete(f"photo:{photo_id}")
    except (ConnectionError, RedisError, OSError):
        return


async def invalidate_comments_cache(photo_id: str) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        await client.delete(f"comments:{photo_id}")
    except (ConnectionError, RedisError, OSError):
        return
