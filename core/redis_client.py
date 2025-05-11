import redis.asyncio as asyncredis
from asgiref.sync import async_to_sync
from core.settings import CONFIG

redis_client = asyncredis.from_url(
    CONFIG["REDIS_URL"]
)

set_sync = async_to_sync(redis_client.set)
get_sync = async_to_sync(redis_client.get)