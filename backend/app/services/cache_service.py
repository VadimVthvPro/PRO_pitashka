import json
import logging
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self, redis_client: aioredis.Redis | None, enabled: bool = True):
        self.redis = redis_client
        self.enabled = enabled and redis_client is not None

    async def get(self, key: str) -> dict | list | None:
        if not self.enabled or not self.redis:
            return None
        try:
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning("Cache get error for key %s: %s", key, e)
            return None

    async def set(self, key: str, value, ttl: int = 3600) -> None:
        if not self.enabled or not self.redis:
            return
        try:
            await self.redis.set(key, json.dumps(value, default=str), ex=ttl)
        except Exception as e:
            logger.warning("Cache set error for key %s: %s", key, e)

    async def delete(self, key: str) -> None:
        if not self.enabled or not self.redis:
            return
        try:
            await self.redis.delete(key)
        except Exception:
            pass
