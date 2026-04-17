import asyncio
import functools
import logging

logger = logging.getLogger(__name__)


def async_retry(attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == attempts:
                        logger.error("%s failed after %d attempts: %s", func.__name__, attempts, e)
                        raise
                    logger.warning("%s attempt %d failed: %s, retrying in %.1fs", func.__name__, attempt, e, current_delay)
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator
