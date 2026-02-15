import os
import redis.asyncio as asyncredis

# Redis client instance (initialized lazily)
_redis_client = None

def get_redis_client():
    global _redis_client
    
    if _redis_client is None:
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_password = os.getenv('REDIS_PASSWORD', None)
        
        # Build Redis URL
        if redis_password:
            redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}"
        else:
            redis_url = f"redis://{redis_host}:{redis_port}"
        
        try:
            _redis_client = asyncredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        except Exception as e:
            print(f"Warning: Could not initialize Redis client: {e}")
            _redis_client = None
    
    return _redis_client

# Synchronous Redis operations (wrappers)
def get_sync(key):
    """Synchronous get from Redis"""
    import asyncio
    client = get_redis_client()
    if client:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If event loop is already running, we can't use run_until_complete
                return None
            return loop.run_until_complete(client.get(key))
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    return None

def set_sync(key, value, ex=None):
    import asyncio
    client = get_redis_client()
    if client:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return None
            return loop.run_until_complete(client.set(key, value, ex=ex))
        except Exception as e:
            print(f"Redis set error: {e}")
            return None
    return None

async def get_async(key):
    client = get_redis_client()
    if client:
        try:
            return await client.get(key)
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    return None

async def set_async(key, value, ex=None):
    client = get_redis_client()
    if client:
        try:
            return await client.set(key, value, ex=ex)
        except Exception as e:
            print(f"Redis set error: {e}")
            return None
    return None
