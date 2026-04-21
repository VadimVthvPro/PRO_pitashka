"""Session + OTP primitives used by every auth provider.

Три концепции в одном модуле:

1. **JWT access/refresh pair** — классический stateless auth. Access
   короткий (1 ч), refresh длинный (90 дней). Refresh хранится в
   `web_sessions.refresh_token_hash`, чтобы мы могли отозвать сессию
   (logout, принудительный ре-логин) не ожидая истечения JWT.

2. **OTP-коды** для Telegram-флоу. До миграции 017 коды искались по
   `telegram_username`, теперь — по самому коду (он уникален среди
   активных благодаря partial unique index'у idx_otp_codes_active_code).
   Код — 6-символьный alphanumeric из «безопасного» алфавита (без O/0/I/1/L):
   32⁶ ≈ 10⁹ комбинаций, достаточно для глобальной уникальности сотен
   одновременно активных кодов. При коллизии INSERT падает с
   UniqueViolationError → в `request_otp_for_user` есть retry-loop.

3. **Синтетический user_id** для провайдеров, где у нас нет Telegram id
   (Google, Yandex, VK). `user_main.user_id` исторически = Telegram id,
   поэтому для non-Telegram регистраций берём id из sequence
   `user_main_synth_id_seq` (стартует с 10¹³ — см. миграцию 016).
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import asyncpg
from asyncpg.exceptions import UniqueViolationError
from jose import jwt

from app.config import get_settings

logger = logging.getLogger(__name__)

# Алфавит без «двусмысленных» символов, которые путаются в сообщениях
# и при рукописном вводе: нет 0/O, 1/I/L. 32 символа → 32⁶ ≈ 10⁹.
_OTP_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_OTP_LENGTH = 6
_OTP_TTL_MINUTES = 15  # дольше, чем раньше: чтобы юзер успел скопировать

# Ограничение на retry при коллизии кода — на практике не срабатывает
# никогда (коллизия ~10⁻⁷ при сотнях активных OTP), но оставляем safety net.
_OTP_INSERT_MAX_RETRIES = 5


def generate_otp_code() -> str:
    """Сгенерировать 6-символьный alphanumeric код.

    Используем `secrets.choice` (CSPRNG), не `random` — OTP не должен
    быть предсказуемым даже локальному пользователю. Алфавит специально
    ограничен, чтобы код было удобно диктовать голосом и вводить с
    клавиатуры на мобильном.
    """
    return "".join(secrets.choice(_OTP_ALPHABET) for _ in range(_OTP_LENGTH))


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


# ============================================================================
# OTP — user_id based (новая схема после миграции 017)
# ============================================================================


async def request_otp_for_user(pool: asyncpg.Pool, user_id: int) -> str | None:
    """Сгенерировать и сохранить свежий OTP для данного user_id.

    Старые неиспользованные коды этого пользователя помечаются used=TRUE,
    чтобы partial unique index не блокировал повторную выдачу и чтобы
    пользователь не путался: один активный код на один user_id.

    Возвращает сам код (его бот тут же шлёт юзеру сообщением).
    """
    expires = datetime.now(timezone.utc) + timedelta(minutes=_OTP_TTL_MINUTES)

    await pool.execute(
        "UPDATE otp_codes SET used = TRUE WHERE user_id = $1 AND used = FALSE",
        user_id,
    )

    for attempt in range(1, _OTP_INSERT_MAX_RETRIES + 1):
        code = generate_otp_code()
        try:
            await pool.execute(
                """
                INSERT INTO otp_codes (user_id, code, expires_at)
                VALUES ($1, $2, $3)
                """,
                user_id, code, expires,
            )
            return code
        except UniqueViolationError:
            # Partial unique index (code WHERE used=FALSE) поймал коллизию.
            # Пробуем ещё раз — новый случайный код.
            if attempt == _OTP_INSERT_MAX_RETRIES:
                logger.error("OTP code collision after %d retries for user %d", attempt, user_id)
                return None
            continue

    return None


async def verify_otp_code(pool: asyncpg.Pool, code: str) -> int | None:
    """Проверить код, полученный от пользователя, и вернуть user_id.

    Не принимает username — lookup идёт по активным кодам глобально.
    Партиальный unique index гарантирует, что активный код однозначен.
    Код case-insensitive ко вводу (алфавит только A-Z2-9, так что
    приводим к upper).
    """
    normalized = code.strip().upper()
    row = await pool.fetchrow(
        """
        SELECT id, user_id FROM otp_codes
        WHERE code = $1
          AND used = FALSE
          AND expires_at > NOW()
          AND user_id IS NOT NULL
        LIMIT 1
        """,
        normalized,
    )
    if not row:
        return None

    await pool.execute("UPDATE otp_codes SET used = TRUE WHERE id = $1", row["id"])
    return row["user_id"]


# ============================================================================
# Sessions
# ============================================================================


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


# ============================================================================
# Synthetic user_id для non-Telegram регистраций
# ============================================================================


async def allocate_synthetic_user_id(pool: asyncpg.Pool) -> int:
    """Вернуть следующий id из sequence `user_main_synth_id_seq`.

    Используется когда мы создаём `user_main` для юзера, пришедшего через
    Google / Yandex / VK и не имеющего Telegram. Sequence стартует с 10^13
    (см. миграцию 016), поэтому никогда не пересекается с реальными
    Telegram-id (~10^10 в 2026 г.).
    """
    return await pool.fetchval("SELECT nextval('user_main_synth_id_seq')")
