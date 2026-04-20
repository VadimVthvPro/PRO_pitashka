"""Квоты на AI-фичи.

Проверка и инкремент используют `usage_counters` (день/месяц), лимиты
берутся из активной подписки юзера через `subscription_service.resolve()`.

Два основных метода:
- `check(user_id, key)` — не увеличивает счётчик, возвращает статус;
- `consume(user_id, key, n=1)` — атомарный инкремент с повторной проверкой
  предела (чтобы параллельные запросы не проскочили).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import asyncpg

from app.repositories.billing_repo import BillingRepository
from app.services import subscription_service

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class QuotaStatus:
    key: str
    limit: int            # -1 = безлимит
    period: str           # 'd' | 'm' | 'static'
    used: int
    allowed: bool
    reset_at: datetime | None
    plan_key: str
    tier: str


class QuotaExceeded(Exception):
    """Брошено, когда юзер упёрся в лимит — превращается в HTTP 402 в route-слое."""

    def __init__(self, status: QuotaStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _reset_at(period: str, today: date | None = None) -> datetime | None:
    """Когда следующее обнуление счётчика."""
    today = today or datetime.now(timezone.utc).date()
    if period == "d":
        return datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    if period == "m":
        # первое число следующего месяца
        if today.month == 12:
            nxt = date(today.year + 1, 1, 1)
        else:
            nxt = date(today.year, today.month + 1, 1)
        return datetime.combine(nxt, datetime.min.time(), tzinfo=timezone.utc)
    return None


def _extract_limit(sub: dict[str, Any], key: str) -> tuple[int, str]:
    """Из `resolve()`-payload достаёт (limit, period) для нужной квоты.

    Если в плане нет такого ключа — безопасный фолбэк: безлимит. Это чтобы
    случайное добавление нового quota_key в код не ломало всех юзеров —
    кто-то увидит предупреждение в логах, остальные работают.
    """
    limits: dict[str, Any] = sub.get("limits") or {}
    entry = limits.get(key)
    if not isinstance(entry, dict):
        logger.warning("quota_service: missing limit '%s' in plan '%s'", key, sub.get("plan_key"))
        return -1, "d"
    limit = int(entry.get("limit", -1))
    period = str(entry.get("period") or "d")
    return limit, period


async def check(
    pool: asyncpg.Pool, redis, user_id: int, quota_key: str
) -> QuotaStatus:
    sub = await subscription_service.resolve(pool, redis, user_id)
    limit, period = _extract_limit(sub, quota_key)
    if limit == -1 or period == "static":
        return QuotaStatus(
            key=quota_key, limit=limit, period=period, used=0, allowed=True,
            reset_at=None, plan_key=sub["plan_key"], tier=sub["tier"],
        )
    used = await BillingRepository(pool).get_usage(user_id, quota_key, period)
    return QuotaStatus(
        key=quota_key, limit=limit, period=period, used=used,
        allowed=used < limit, reset_at=_reset_at(period),
        plan_key=sub["plan_key"], tier=sub["tier"],
    )


async def consume(
    pool: asyncpg.Pool, redis, user_id: int, quota_key: str, *, n: int = 1
) -> QuotaStatus:
    """Атомарно: проверяем лимит, потом инкрементируем. Если за время между
    двумя шагами кто-то исчерпал лимит — откатываем инкремент и кидаем
    `QuotaExceeded`.
    """
    status = await check(pool, redis, user_id, quota_key)
    if status.limit == -1 or status.period == "static":
        return status
    if not status.allowed:
        raise QuotaExceeded(
            status,
            _default_message(status),
        )
    repo = BillingRepository(pool)
    new_used = await repo.increment_usage(user_id, quota_key, status.period, n=n)
    if new_used > status.limit:
        # Перекрутили — откатываем и возвращаем «исчерпано».
        await repo.increment_usage(user_id, quota_key, status.period, n=-n)
        status.used = status.limit
        status.allowed = False
        raise QuotaExceeded(status, _default_message(status))
    status.used = new_used
    status.allowed = True
    return status


async def get_all_status(
    pool: asyncpg.Pool, redis, user_id: int
) -> list[QuotaStatus]:
    """Для UI — статус по всем ключам плана."""
    sub = await subscription_service.resolve(pool, redis, user_id)
    limits: dict[str, Any] = sub.get("limits") or {}
    usage = await BillingRepository(pool).get_all_usage(user_id)
    out: list[QuotaStatus] = []
    for key, entry in limits.items():
        if not isinstance(entry, dict):
            continue
        limit = int(entry.get("limit", -1))
        period = str(entry.get("period") or "d")
        if period == "static":
            used = 0
        else:
            used = int(usage.get(key, {}).get(period, 0))
        out.append(QuotaStatus(
            key=key, limit=limit, period=period, used=used,
            allowed=(limit == -1) or (used < limit),
            reset_at=_reset_at(period),
            plan_key=sub["plan_key"], tier=sub["tier"],
        ))
    return out


def _default_message(status: QuotaStatus) -> str:
    human = {
        "ai_chat_msg": "AI-сообщений",
        "ai_photo": "фото-анализов",
        "ai_meal_plan": "планов питания",
        "ai_workout_plan": "планов тренировок",
        "ai_recipe": "AI-рецептов",
        "ai_digest": "AI-дайджестов",
        "food_manual": "записей о еде",
        "social_post_photo": "фото-постов",
    }.get(status.key, status.key)
    period = "на сегодня" if status.period == "d" else "в этом месяце"
    return f"Лимит {human} {period} исчерпан ({status.used}/{status.limit}). Открой Premium."
