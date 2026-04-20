import json
import logging

import asyncpg

from app.config import get_settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db() first.")
    return _pool


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Register codecs so JSONB fields round-trip as plain Python dicts/lists.

    Without this asyncpg returns JSONB as a raw `str`, which silently breaks
    every `dict(row["payload"])` / `dict(row["detail"])` callsite (500 errors
    in social, admin/audit, …). Registering once per connection makes it
    impossible to forget elsewhere.
    """
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def init_db() -> None:
    global _pool
    settings = get_settings()
    _pool = await asyncpg.create_pool(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        min_size=settings.DB_POOL_MIN,
        max_size=settings.DB_POOL_MAX,
        command_timeout=settings.API_TIMEOUT,
        init=_init_connection,
    )
    logger.info("Database pool created (%d-%d connections)", settings.DB_POOL_MIN, settings.DB_POOL_MAX)


async def close_db() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")
