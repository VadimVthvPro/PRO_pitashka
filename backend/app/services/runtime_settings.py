"""Runtime settings cache backed by `app_settings` (JSONB key/value).

Why a separate service:

Values in `.env` are fine for secrets (API keys, DB creds) but terrible for
operational knobs that must change *without redeploy* — AI model, retry
budgets, free-tier daily quota, feature toggles. Those live in Postgres so
the admin panel can edit them live.

The cache is process-local with a short TTL. On a multi-replica deploy this
means a change takes at most ``_TTL`` seconds to propagate everywhere, which
is fine for operator-driven changes. If we ever need instant invalidation we
can wire a pub/sub channel later.

All accessors have a hard-coded env fallback so deployments where the DB is
being restored / migrations are still running keep serving requests.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

from app.config import get_settings
from app import database as _db

logger = logging.getLogger(__name__)


def _pool_or_none():
    """Return the active pool or None if DB isn't ready — never raise.

    Used on paths (runtime settings read) that must not crash during boot
    or during a short migration window.
    """
    return _db._pool  # noqa: SLF001 — intentional, pool is module-level singleton

_TTL = 30.0  # seconds — tight enough for admin edits, relaxed enough to avoid hot path hits


# Known keys: default + optional description for admin UI. Anything not listed
# here is still readable, but won't show up in the "known settings" listing.
KNOWN_SETTINGS: dict[str, dict[str, Any]] = {
    "gemini_model": {
        "default": "gemini-2.5-flash",
        "type": "string",
        "description": "Модель Gemini, которую использует AI-сервис.",
        "group": "ai",
    },
    "gemini_per_call_timeout": {
        "default": 60.0,
        "type": "float",
        "description": "Сколько секунд ждём один вызов до таймаута.",
        "group": "ai",
    },
    "gemini_retry_attempts": {
        "default": 5,
        "type": "int",
        "description": "Максимум попыток при транзитных ошибках.",
        "group": "ai",
    },
    "gemini_retry_total_budget": {
        "default": 150.0,
        "type": "float",
        "description": "Общий бюджет retry на один пользовательский запрос.",
        "group": "ai",
    },
    "free_ai_daily_limit": {
        "default": 20,
        "type": "int",
        "description": "Сколько ответов AI может получить free-юзер в сутки.",
        "group": "quota",
    },
    "free_meal_plan_monthly_limit": {
        "default": 2,
        "type": "int",
        "description": "Сколько планов питания может собрать free-юзер в месяц.",
        "group": "quota",
    },
    "social_posting_enabled": {
        "default": True,
        "type": "bool",
        "description": "Глобальный рубильник публикации постов (на случай инцидента).",
        "group": "features",
    },
    "google_signup_enabled": {
        "default": True,
        "type": "bool",
        "description": "Показывать ли кнопку входа через Google.",
        "group": "features",
    },
    "ai_chat_enabled": {
        "default": True,
        "type": "bool",
        "description": "Доступен ли AI-чат (на случай отказа Gemini).",
        "group": "features",
    },
}


_cache: dict[str, tuple[float, Any]] = {}
_lock = asyncio.Lock()


def _env_fallback(key: str) -> Any:
    """Fallback to env for a handful of keys so we survive a cold DB."""
    if key == "gemini_model":
        return get_settings().GEMINI_MODEL or KNOWN_SETTINGS[key]["default"]
    spec = KNOWN_SETTINGS.get(key)
    return spec["default"] if spec else None


def _unwrap(v: Any) -> Any:
    """JSONB scalars come back as-is (codec-decoded), but legacy rows may
    have a wrapper dict or a string — normalise both."""
    if isinstance(v, (bytes, bytearray)):
        v = v.decode("utf-8")
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            return v
    if isinstance(v, dict) and set(v.keys()) == {"value"}:
        return v["value"]
    return v


async def _fetch_from_db(key: str) -> Optional[Any]:
    pool = _pool_or_none()
    if pool is None:
        return None
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM app_settings WHERE key = $1", key
            )
    except Exception as e:
        logger.debug("runtime_settings: fetch failed for %s: %s", key, e)
        return None
    if row is None:
        return None
    return _unwrap(row["value"])


async def get_setting(key: str) -> Any:
    """Read a runtime setting. Cached for ``_TTL`` seconds per process.

    Never raises — any failure degrades to the env-backed default.
    """
    now = time.monotonic()
    cached = _cache.get(key)
    if cached and cached[0] > now:
        return cached[1]
    async with _lock:
        # Re-check under lock to avoid dog-piling.
        cached = _cache.get(key)
        if cached and cached[0] > now:
            return cached[1]
        value = await _fetch_from_db(key)
        if value is None:
            value = _env_fallback(key)
        _cache[key] = (now + _TTL, value)
        return value


def _coerce(key: str, raw: Any) -> Any:
    """Coerce user-provided value to the declared type (int/float/bool/string)."""
    spec = KNOWN_SETTINGS.get(key)
    if not spec:
        return raw
    t = spec["type"]
    if t == "int":
        return int(raw)
    if t == "float":
        return float(raw)
    if t == "bool":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return bool(raw)
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on"}
        return bool(raw)
    return str(raw)


async def set_setting(key: str, raw_value: Any, updated_by: Optional[int] = None) -> Any:
    """Upsert a value and bust the process cache. Returns the stored value."""
    value = _coerce(key, raw_value)
    pool = _pool_or_none()
    if pool is None:
        raise RuntimeError("Database pool is not available")
    async with pool.acquire() as conn:
        # jsonb codec (see database.py) serialises python values for us, so we
        # pass the typed value directly — json.dumps would double-encode.
        await conn.execute(
            """
            INSERT INTO app_settings (key, value, description, updated_at, updated_by)
            VALUES ($1, $2::jsonb, $3, NOW(), $4)
            ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value,
                description = COALESCE(EXCLUDED.description, app_settings.description),
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            """,
            key,
            value,
            (KNOWN_SETTINGS.get(key) or {}).get("description"),
            updated_by,
        )
    _cache[key] = (time.monotonic() + _TTL, value)
    return value


async def list_settings() -> list[dict[str, Any]]:
    """List every known setting with current value, origin and metadata."""
    pool = _pool_or_none()
    overrides: dict[str, Any] = {}
    updates: dict[str, Any] = {}
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT key, value, description, updated_at FROM app_settings"
                )
            for r in rows:
                overrides[r["key"]] = _unwrap(r["value"])
                updates[r["key"]] = r["updated_at"]
        except Exception as e:
            logger.debug("list_settings: DB read failed: %s", e)

    out = []
    for key, spec in KNOWN_SETTINGS.items():
        current = overrides.get(key, _env_fallback(key))
        out.append({
            "key": key,
            "type": spec["type"],
            "group": spec["group"],
            "description": spec["description"],
            "default": spec["default"],
            "value": current,
            "overridden": key in overrides,
            "updated_at": updates[key].isoformat() if key in updates else None,
        })
    return out


def invalidate_cache() -> None:
    _cache.clear()
