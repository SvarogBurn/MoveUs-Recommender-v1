import asyncio
import functools

import redis.asyncio as asyncredis

from core.settings import CONFIG

redis_client = asyncredis.from_url(
    CONFIG["REDIS_URL"]
)

def sync_wrapper(func_name):
    @functools.wraps(func_name)
    def wrapper(*args, **kwargs):
        async def run():
            redis_client = asyncredis.from_url(CONFIG["REDIS_URL"])
            func = getattr(redis_client, func_name)
            result = await func(*args, **kwargs)
            await redis_client.close()
            return result
        return asyncio.run(run())
    return wrapper

set_sync = sync_wrapper("set")
get_sync = sync_wrapper("get")
