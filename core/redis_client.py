import asyncio
import functools

import redis.asyncio as asyncredis

from core.settings import CONFIG

redis_client = asyncredis.from_url(
    CONFIG["REDIS_URL"]
)

def sync_wrapper(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper

set_sync = sync_wrapper(redis_client.set)
get_sync = sync_wrapper(redis_client.get)