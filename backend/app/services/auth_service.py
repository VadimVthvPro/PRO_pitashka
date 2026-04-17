import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt
import asyncpg
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


def generate_otp() -> str:
    return f"{secrets.randbelow(10000):04d}"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "access"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(user_id: int) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "refresh"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        return None


async def request_otp(pool: asyncpg.Pool, telegram_username: str) -> str | None:
    code = generate_otp()
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)

    await pool.execute(
        "UPDATE otp_codes SET used = TRUE WHERE telegram_username = $1 AND used = FALSE",
        telegram_username,
    )

    await pool.execute(
        "INSERT INTO otp_codes (telegram_username, code, expires_at) VALUES ($1, $2, $3)",
        telegram_username, code, expires,
    )
    return code


async def verify_otp(pool: asyncpg.Pool, telegram_username: str, code: str) -> int | None:
    row = await pool.fetchrow(
        """
        SELECT id, user_id FROM otp_codes
        WHERE telegram_username = $1
          AND code = $2
          AND used = FALSE
          AND expires_at > NOW()
        ORDER BY created_at DESC
        LIMIT 1
        """,
        telegram_username, code,
    )
    if not row:
        return None

    await pool.execute("UPDATE otp_codes SET used = TRUE WHERE id = $1", row["id"])

    user_row = await pool.fetchrow(
        "SELECT user_id FROM user_main WHERE telegram_username = $1",
        telegram_username.lower(),
    )

    if user_row:
        return user_row["user_id"]

    return None


async def create_session(
    pool: asyncpg.Pool,
    user_id: int,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[str, str]:
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)

    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    await pool.execute(
        """
        INSERT INTO web_sessions (user_id, token_hash, refresh_token_hash, expires_at, user_agent, ip_address)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        user_id, hash_token(access), hash_token(refresh), expires, user_agent, ip_address,
    )
    return access, refresh


async def refresh_session(pool: asyncpg.Pool, refresh_token: str) -> tuple[str, str] | None:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return None

    user_id = int(payload["sub"])
    token_hash = hash_token(refresh_token)

    session = await pool.fetchrow(
        "SELECT id FROM web_sessions WHERE refresh_token_hash = $1 AND expires_at > NOW()",
        token_hash,
    )
    if not session:
        return None

    await pool.execute("DELETE FROM web_sessions WHERE id = $1", session["id"])
    return await create_session(pool, user_id)


async def invalidate_session(pool: asyncpg.Pool, access_token: str) -> None:
    token_hash = hash_token(access_token)
    await pool.execute("DELETE FROM web_sessions WHERE token_hash = $1", token_hash)
