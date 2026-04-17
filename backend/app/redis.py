import redis.asyncio as aioredis
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None
_available: bool = False


async def get_redis() -> aioredis.Redis | None:
    if not _available:
        return None
    return _redis


async def init_redis() -> None:
    global _redis, _available
    settings = get_settings()
    try:
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await _redis.ping()
        _available = True
        logger.info("Redis connected at %s:%d", settings.REDIS_HOST, settings.REDIS_PORT)
    except Exception as e:
        logger.warning("Redis unavailable (%s), caching disabled", e)
        _redis = None
        _available = False


async def close_redis() -> None:
    global _redis, _available
    if _redis:
        await _redis.close()
        _redis = None
        _available = False
        logger.info("Redis connection closed")
