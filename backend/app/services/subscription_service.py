"""Определение текущего тира пользователя и выдача/отзыв подписок.

Правила:
- активной считается запись в `subscriptions` со `status='active'` и
  `end_at > NOW()`. Если таких несколько — берём самую позднюю по `end_at`.
- если активной нет — юзер на `free`.
- `grant()` атомарно закрывает все предыдущие active-подписки юзера и
  создаёт новую, плюс синхронизирует `user_main.is_premium`/`premium_until`
  для обратной совместимости с существующим кодом (функции в схеме,
  админка и т.д.).
- результат `resolve()` кешируется в Redis на 60 секунд, чтобы не дёргать
  БД при каждом проверенном endpoint'е.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg

from app.repositories.billing_repo import BillingRepository

logger = logging.getLogger(__name__)


_FREE_CACHE: dict[str, Any] = {
    "tier": "free",
    "plan_key": "free",
    "name": "Free",
    "end_at": None,
    "status": "active",
    "source": None,
    "features": [],
}


async def _cache_get(redis, user_id: int) -> dict[str, Any] | None:
    if redis is None:
        return None
    try:
        raw = await redis.get(f"sub:{user_id}")
        if raw:
            return json.loads(raw)
    except Exception:
        return None
    return None


async def _cache_set(redis, user_id: int, data: dict[str, Any]) -> None:
    if redis is None:
        return
    try:
        # Невозможно серилизовать datetime — переводим в isoformat.
        safe = dict(data)
        if isinstance(safe.get("end_at"), datetime):
            safe["end_at"] = safe["end_at"].isoformat()
        await redis.setex(f"sub:{user_id}", 60, json.dumps(safe, ensure_ascii=False))
    except Exception:
        pass


async def _cache_invalidate(redis, user_id: int) -> None:
    if redis is None:
        return
    try:
        await redis.delete(f"sub:{user_id}")
    except Exception:
        pass


async def _fetch_free_plan(pool: asyncpg.Pool) -> dict[str, Any]:
    row = await BillingRepository(pool).get_plan("free")
    if row:
        return {
            "tier": "free",
            "plan_key": "free",
            "name": row.get("name", "Free"),
            "limits": row.get("limits", {}),
            "features": row.get("features", []),
            "end_at": None,
            "status": "active",
            "source": None,
            "duration_days": None,
            "price_stars": 0,
            "price_usd_cents": 0,
        }
    # Fallback на случай пустого справочника — всё равно отдаём free.
    return dict(_FREE_CACHE)


async def resolve(pool: asyncpg.Pool, redis, user_id: int) -> dict[str, Any]:
    """Возвращает текущий тир юзера в плоском dict-виде.

    Shape:
        {
            "tier": "free|premium|pro",
            "plan_key": "free|premium_month|…",
            "name": "Free|Premium|…",
            "limits": {quota_key: {"limit": int, "period": "d|m|static"}},
            "features": [...],
            "end_at": datetime|None,
            "status": "active|expired",
            "source": "stars|card|promo|admin|None",
        }
    """
    cached = await _cache_get(redis, user_id)
    if cached:
        if isinstance(cached.get("end_at"), str):
            try:
                cached["end_at"] = datetime.fromisoformat(cached["end_at"])
            except Exception:
                cached["end_at"] = None
        return cached

    repo = BillingRepository(pool)
    sub = await repo.get_active_subscription(user_id)
    if sub:
        result = {
            "tier": sub["tier"],
            "plan_key": sub["plan_key"],
            "name": sub["name"],
            "limits": sub.get("limits", {}) or {},
            "features": sub.get("features", []) or [],
            "end_at": sub["end_at"],
            "status": sub["status"],
            "source": sub["source"],
            "duration_days": sub.get("duration_days"),
        }
    else:
        result = await _fetch_free_plan(pool)

    await _cache_set(redis, user_id, result)
    return result


async def grant(
    pool: asyncpg.Pool,
    redis,
    *,
    user_id: int,
    plan_key: str,
    source: str,
    payment_id: int | None = None,
    start_from: datetime | None = None,
) -> dict[str, Any]:
    """Выдаёт юзеру подписку по `plan_key`. Идемпотентно относительно payment_id:
    повторный вызов с тем же payment_id не создаёт дублей.

    Возвращает свежий `resolve()`-payload.
    """
    repo = BillingRepository(pool)
    plan = await repo.get_plan(plan_key)
    if plan is None:
        raise ValueError(f"Unknown plan_key: {plan_key}")
    if plan["tier"] == "free" or not plan.get("duration_days"):
        raise ValueError(f"Plan {plan_key} is not grantable")

    now = datetime.now(timezone.utc)
    start_at = start_from or now

    # Если у юзера уже есть активная подписка того же tier-а — продлеваем,
    # добавляя duration_days к её end_at. Иначе отсчитываем от now.
    existing = await repo.get_active_subscription(user_id)
    if existing and existing["tier"] == plan["tier"] and existing["end_at"] > now:
        start_at = existing["end_at"]

    end_at = start_at + timedelta(days=int(plan["duration_days"]))

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Защита от повторов: если payment_id уже привязан к существующей
            # подписке — не создаём вторую.
            if payment_id is not None:
                dup = await conn.fetchrow(
                    "SELECT id FROM subscriptions WHERE payment_id = $1",
                    payment_id,
                )
                if dup:
                    logger.info("subscription.grant: payment_id=%s already granted, skip", payment_id)
                    await _cache_invalidate(redis, user_id)
                    return await resolve(pool, redis, user_id)

            await repo.expire_active_subscriptions(conn, user_id)
            sub_id = await repo.insert_subscription(
                conn,
                user_id=user_id,
                plan_key=plan_key,
                tier=plan["tier"],
                status="active",
                source=source,
                start_at=start_at,
                end_at=end_at,
                payment_id=payment_id,
            )
            # Обновляем легаси-поля в user_main, чтобы остальная кодовая база
            # (админка, функции БД) продолжала работать без переписывания.
            await conn.execute(
                """
                UPDATE user_main
                   SET is_premium    = TRUE,
                       premium_until = $2
                 WHERE user_id = $1
                """,
                user_id, end_at.replace(tzinfo=None),
            )

    await _cache_invalidate(redis, user_id)
    logger.info(
        "subscription.grant user=%s plan=%s tier=%s end=%s source=%s payment=%s sub_id=%s",
        user_id, plan_key, plan["tier"], end_at.isoformat(), source, payment_id, sub_id,
    )
    return await resolve(pool, redis, user_id)


async def cancel_auto_renew(pool: asyncpg.Pool, redis, user_id: int) -> None:
    """Отключает auto_renew на активной подписке. Саму подписку не трогает —
    она доживёт до `end_at`, а потом перейдёт в `expired` при следующем
    `resolve()`.
    """
    await pool.execute(
        """
        UPDATE subscriptions
           SET auto_renew = FALSE
         WHERE user_id = $1 AND status = 'active'
        """,
        user_id,
    )
    await _cache_invalidate(redis, user_id)


async def admin_expire_all(pool: asyncpg.Pool, redis, user_id: int) -> None:
    """Жёсткое закрытие всех active-подписок — используется при refund."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            await BillingRepository(pool).expire_active_subscriptions(conn, user_id)
            await conn.execute(
                "UPDATE user_main SET is_premium = FALSE, premium_until = NULL WHERE user_id = $1",
                user_id,
            )
    await _cache_invalidate(redis, user_id)


async def handle_refund(pool: asyncpg.Pool, redis, *, telegram_payment_charge_id: str) -> bool:
    """Обрабатывает refund по Stars: помечает платёж и отзывает подписку.

    Возвращает True, если что-то действительно откатили.
    """
    repo = BillingRepository(pool)
    payment = await repo.get_star_payment_by_charge(telegram_payment_charge_id)
    if not payment:
        logger.warning("handle_refund: payment not found for charge_id=%s", telegram_payment_charge_id)
        return False
    await repo.mark_payment_refunded(payment["id"])
    await admin_expire_all(pool, redis, payment["user_id"])
    return True
