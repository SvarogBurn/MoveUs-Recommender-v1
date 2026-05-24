import logging
import os
from typing import Any

import redis
import redis.asyncio as asyncredis

logger = logging.getLogger(__name__)

_async_client: asyncredis.Redis | None = None
_sync_client: redis.Redis | None = None


def _build_url() -> str:
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD")
    if password:
        return f"redis://:{password}@{host}:{port}"
    return f"redis://{host}:{port}"


def get_redis_client() -> asyncredis.Redis | None:
    global _async_client
    if _async_client is None:
        try:
            _async_client = asyncredis.from_url(
                _build_url(), encoding="utf-8", decode_responses=True
            )
        except Exception as e:
            logger.warning("Could not initialize async Redis client: %s", e)
            _async_client = None
    return _async_client


def _get_sync_client() -> redis.Redis | None:
    global _sync_client
    if _sync_client is None:
        try:
            _sync_client = redis.Redis.from_url(
                _build_url(), encoding="utf-8", decode_responses=True
            )
        except Exception as e:
            logger.warning("Could not initialize sync Redis client: %s", e)
            _sync_client = None
    return _sync_client


def get_sync(key: str) -> str | None:
    client = _get_sync_client()
    if client is None:
        return None
    try:
        return client.get(key)
    except Exception as e:
        logger.error("Redis get error: %s", e)
        return None


def set_sync(key: str, value: Any, ex: int | None = None) -> bool | None:
    client = _get_sync_client()
    if client is None:
        return None
    try:
        return client.set(key, value, ex=ex)
    except Exception as e:
        logger.error("Redis set error: %s", e)
        return None


def incr_sync(key: str, ex: int | None = None) -> int | None:
    """Atomically increment a counter; optionally set expiry on first write."""
    client = _get_sync_client()
    if client is None:
        return None
    try:
        pipe = client.pipeline()
        pipe.incr(key)
        if ex is not None:
            pipe.expire(key, ex)
        result = pipe.execute()
        return result[0]
    except Exception as e:
        logger.error("Redis incr error: %s", e)
        return None


async def get_async(key: str) -> Any | None:
    client = get_redis_client()
    if client:
        try:
            return await client.get(key)
        except Exception as e:
            logger.error("Redis get error: %s", e)
            return None
    return None


async def set_async(key: str, value: Any, ex: int | None = None) -> bool | None:
    client = get_redis_client()
    if client:
        try:
            return await client.set(key, value, ex=ex)
        except Exception as e:
            logger.error("Redis set error: %s", e)
            return None
    return None
