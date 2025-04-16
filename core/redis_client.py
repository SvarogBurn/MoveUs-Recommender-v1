import redis.asyncio as asyncredis
from core.settings import CONFIG

redis_client = asyncredis.from_url(
    CONFIG["REDIS_URL"]
)