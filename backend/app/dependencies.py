from typing import Annotated
import asyncpg
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status, Request
from jose import jwt, JWTError

from app.config import Settings, get_settings
from app.database import get_pool
from app.redis import get_redis


SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_db() -> asyncpg.Pool:
    return await get_pool()

DbDep = Annotated[asyncpg.Pool, Depends(get_db)]


async def get_redis_client() -> aioredis.Redis | None:
    return await get_redis()

RedisDep = Annotated[aioredis.Redis | None, Depends(get_redis_client)]


async def get_current_user_id(request: Request, settings: SettingsDep) -> int:
    token = request.cookies.get(settings.AUTH_COOKIE_PREFIX + "access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        uid = int(user_id)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    pool = await get_pool()
    banned = await pool.fetchval(
        "SELECT banned_at FROM user_main WHERE user_id = $1", uid,
    )
    if banned is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")

    return uid


CurrentUserDep = Annotated[int, Depends(get_current_user_id)]
