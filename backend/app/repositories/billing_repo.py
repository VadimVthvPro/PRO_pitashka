"""DB-access слой биллинга.

Все запросы к `tier_plans`, `subscriptions`, `star_payments`, `usage_counters`
живут здесь. Сервисы (`subscription_service`, `quota_service`) оборачивают
эти вызовы бизнес-логикой.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Any

import asyncpg


logger = logging.getLogger(__name__)


def _as_dict(row: asyncpg.Record | None) -> dict[str, Any] | None:
    if row is None:
        return None
    out: dict[str, Any] = dict(row)
    # asyncpg раскодирует JSONB в строку — распарсим заранее, чтобы не
    # заставлять каждого вызывающего помнить об этом.
    for key in ("limits", "features"):
        v = out.get(key)
        if isinstance(v, str):
            try:
                out[key] = json.loads(v)
            except Exception:
                pass
    return out


class BillingRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    # -- tier_plans -------------------------------------------------------

    async def list_plans(self, *, include_free: bool = True) -> list[dict[str, Any]]:
        rows = await self.pool.fetch(
            """
            SELECT plan_key, name, tier, duration_days, price_stars,
                   price_usd_cents, limits, features, sort_order
            FROM tier_plans
            WHERE is_active = TRUE
              AND ($1 OR tier <> 'free')
            ORDER BY sort_order, plan_key
            """,
            include_free,
        )
        return [d for r in rows if (d := _as_dict(r)) is not None]

    async def get_plan(self, plan_key: str) -> dict[str, Any] | None:
        row = await self.pool.fetchrow(
            """
            SELECT plan_key, name, tier, duration_days, price_stars,
                   price_usd_cents, limits, features
            FROM tier_plans
            WHERE plan_key = $1 AND is_active = TRUE
            """,
            plan_key,
        )
        return _as_dict(row)

    # -- subscriptions ----------------------------------------------------

    async def get_active_subscription(self, user_id: int) -> dict[str, Any] | None:
        row = await self.pool.fetchrow(
            """
            SELECT s.id, s.user_id, s.plan_key, s.tier, s.status, s.source,
                   s.start_at, s.end_at, s.auto_renew, s.payment_id,
                   tp.name, tp.limits, tp.features, tp.duration_days
            FROM subscriptions s
            JOIN tier_plans tp ON tp.plan_key = s.plan_key
            WHERE s.user_id = $1 AND s.status = 'active' AND s.end_at > NOW()
            ORDER BY s.end_at DESC
            LIMIT 1
            """,
            user_id,
        )
        return _as_dict(row)

    async def list_subscriptions(self, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        rows = await self.pool.fetch(
            """
            SELECT id, plan_key, tier, status, source, start_at, end_at, created_at
            FROM subscriptions
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            user_id, limit,
        )
        return [dict(r) for r in rows]

    async def insert_subscription(
        self,
        conn: asyncpg.Connection,
        *,
        user_id: int,
        plan_key: str,
        tier: str,
        status: str,
        source: str,
        start_at: datetime,
        end_at: datetime,
        payment_id: int | None,
    ) -> int:
        sub_id = await conn.fetchval(
            """
            INSERT INTO subscriptions
                (user_id, plan_key, tier, status, source, start_at, end_at, payment_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
            """,
            user_id, plan_key, tier, status, source, start_at, end_at, payment_id,
        )
        return int(sub_id)

    async def expire_active_subscriptions(self, conn: asyncpg.Connection, user_id: int) -> None:
        """Закрывает все active-подписки юзера — вызывается перед grant().

        Используется при апгрейде плана или refund, чтобы одновременно
        существовала ровно одна active-подписка.
        """
        await conn.execute(
            """
            UPDATE subscriptions
               SET status = 'expired'
             WHERE user_id = $1 AND status = 'active'
            """,
            user_id,
        )

    async def set_subscription_status(
        self, user_id: int, sub_id: int, status: str
    ) -> None:
        await self.pool.execute(
            "UPDATE subscriptions SET status = $3 WHERE user_id = $1 AND id = $2",
            user_id, sub_id, status,
        )

    # -- star_payments ----------------------------------------------------

    async def create_star_payment(
        self,
        *,
        user_id: int,
        plan_key: str,
        invoice_payload: str,
        stars_amount: int,
    ) -> int:
        return int(await self.pool.fetchval(
            """
            INSERT INTO star_payments
                (user_id, plan_key, invoice_payload, stars_amount, status)
            VALUES ($1, $2, $3, $4, 'pending')
            RETURNING id
            """,
            user_id, plan_key, invoice_payload, stars_amount,
        ))

    async def get_star_payment_by_payload(
        self, payload: str
    ) -> dict[str, Any] | None:
        row = await self.pool.fetchrow(
            """
            SELECT id, user_id, plan_key, invoice_payload, stars_amount, status,
                   telegram_payment_charge_id, provider_payment_charge_id,
                   created_at, paid_at, refunded_at
            FROM star_payments
            WHERE invoice_payload = $1
            """,
            payload,
        )
        return dict(row) if row else None

    async def get_star_payment_by_charge(
        self, charge_id: str
    ) -> dict[str, Any] | None:
        row = await self.pool.fetchrow(
            """
            SELECT id, user_id, plan_key, invoice_payload, stars_amount, status,
                   telegram_payment_charge_id
            FROM star_payments
            WHERE telegram_payment_charge_id = $1
            """,
            charge_id,
        )
        return dict(row) if row else None

    async def mark_payment_paid(
        self,
        conn: asyncpg.Connection,
        *,
        payment_id: int,
        telegram_payment_charge_id: str,
        provider_payment_charge_id: str | None,
    ) -> None:
        await conn.execute(
            """
            UPDATE star_payments
               SET status                       = 'paid',
                   paid_at                      = NOW(),
                   telegram_payment_charge_id   = $2,
                   provider_payment_charge_id   = $3
             WHERE id = $1
            """,
            payment_id, telegram_payment_charge_id, provider_payment_charge_id,
        )

    async def mark_payment_refunded(self, payment_id: int) -> None:
        await self.pool.execute(
            """
            UPDATE star_payments
               SET status = 'refunded', refunded_at = NOW()
             WHERE id = $1
            """,
            payment_id,
        )

    async def list_user_payments(self, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        rows = await self.pool.fetch(
            """
            SELECT id, plan_key, invoice_payload, stars_amount, status,
                   created_at, paid_at, refunded_at
            FROM star_payments
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            user_id, limit,
        )
        return [dict(r) for r in rows]

    # -- usage_counters ---------------------------------------------------

    @staticmethod
    def period_start(period: str, today: date | None = None) -> date:
        today = today or datetime.now(timezone.utc).date()
        if period == "d":
            return today
        if period == "m":
            return today.replace(day=1)
        return today  # 'static' / unknown — не используется, но для типов

    async def get_usage(
        self, user_id: int, quota_key: str, period: str
    ) -> int:
        start = self.period_start(period)
        row = await self.pool.fetchval(
            """
            SELECT count FROM usage_counters
            WHERE user_id = $1 AND quota_key = $2 AND period = $3 AND period_start = $4
            """,
            user_id, quota_key, period, start,
        )
        return int(row or 0)

    async def increment_usage(
        self, user_id: int, quota_key: str, period: str, *, n: int = 1
    ) -> int:
        """Атомарно инкрементирует счётчик, возвращает новое значение.

        UPSERT по (user_id, quota_key, period, period_start). Переход через
        сутки/месяц создаёт новую запись сам по себе — старые остаются для
        последующей аналитики.
        """
        start = self.period_start(period)
        return int(await self.pool.fetchval(
            """
            INSERT INTO usage_counters (user_id, quota_key, period, period_start, count, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (user_id, quota_key, period, period_start) DO UPDATE
                SET count = usage_counters.count + EXCLUDED.count,
                    updated_at = NOW()
            RETURNING count
            """,
            user_id, quota_key, period, start, n,
        ))

    async def get_all_usage(self, user_id: int) -> dict[str, dict[str, int]]:
        """Возвращает все актуальные (today / this month) счётчики юзера.

        Формат: `{"ai_chat_msg": {"d": 7, "m": 0}, …}`. Ключи добавляются
        только там, где хоть одна запись есть.
        """
        today = datetime.now(timezone.utc).date()
        month_start = today.replace(day=1)
        rows = await self.pool.fetch(
            """
            SELECT quota_key, period, count
            FROM usage_counters
            WHERE user_id = $1
              AND (
                (period = 'd' AND period_start = $2) OR
                (period = 'm' AND period_start = $3)
              )
            """,
            user_id, today, month_start,
        )
        out: dict[str, dict[str, int]] = {}
        for r in rows:
            out.setdefault(r["quota_key"], {})[r["period"]] = int(r["count"])
        return out
