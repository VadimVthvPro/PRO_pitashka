"""Freemium billing tables: tier_plans, subscriptions, star_payments, usage_counters.

Revision ID: 011_freemium
Revises: 010_chat_feedback
Create Date: 2026-04-15

Adds the full freemium schema + Telegram-Stars billing so the app can gate
heavy AI features per tier.

* `tier_plans`       — справочник тарифов (free/premium_month/premium_year/…)
                        с лимитами в JSONB. Сидим в этой же миграции, чтобы не
                        тянуть init_seed.sql.
* `subscriptions`    — история подписок пользователя (одна active на
                        user_id; остальные expired/cancelled/refunded).
* `star_payments`    — все попытки оплаты Stars-инвойсами, с
                        telegram_payment_charge_id для /refund.
* `usage_counters`   — дневные/месячные счётчики потребления квот,
                        уникальны по (user_id, quota_key, period, period_start).

Старые колонки `user_main.is_premium` / `premium_until` оставлены ради
совместимости с существующим кодом и админкой — их синхронизирует
`subscription_service.grant()`.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "011_freemium"
down_revision: Union[str, None] = "010_chat_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tier_plans (
            plan_key         VARCHAR(32) PRIMARY KEY,
            name             VARCHAR(64) NOT NULL,
            tier             VARCHAR(16) NOT NULL,
            duration_days    INTEGER,
            price_stars      INTEGER NOT NULL DEFAULT 0,
            price_usd_cents  INTEGER,
            limits           JSONB NOT NULL DEFAULT '{}'::jsonb,
            features         JSONB NOT NULL DEFAULT '[]'::jsonb,
            is_active        BOOLEAN NOT NULL DEFAULT TRUE,
            sort_order       INTEGER DEFAULT 0,
            created_at       TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id           BIGSERIAL PRIMARY KEY,
            user_id      BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
            plan_key     VARCHAR(32) NOT NULL REFERENCES tier_plans(plan_key),
            tier         VARCHAR(16) NOT NULL,
            status       VARCHAR(16) NOT NULL,
            source       VARCHAR(16) NOT NULL,
            start_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            end_at       TIMESTAMPTZ NOT NULL,
            auto_renew   BOOLEAN NOT NULL DEFAULT FALSE,
            payment_id   BIGINT,
            created_at   TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status
            ON subscriptions(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_end_at_active
            ON subscriptions(end_at) WHERE status = 'active';

        CREATE TABLE IF NOT EXISTS star_payments (
            id                           BIGSERIAL PRIMARY KEY,
            user_id                      BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
            plan_key                     VARCHAR(32) NOT NULL,
            invoice_payload              VARCHAR(128) NOT NULL UNIQUE,
            stars_amount                 INTEGER NOT NULL,
            status                       VARCHAR(16) NOT NULL DEFAULT 'pending',
            telegram_payment_charge_id   VARCHAR(128),
            provider_payment_charge_id   VARCHAR(128),
            created_at                   TIMESTAMPTZ DEFAULT NOW(),
            paid_at                      TIMESTAMPTZ,
            refunded_at                  TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS idx_star_payments_user_status
            ON star_payments(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_star_payments_charge_id
            ON star_payments(telegram_payment_charge_id)
            WHERE telegram_payment_charge_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS usage_counters (
            user_id       BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
            quota_key     VARCHAR(32) NOT NULL,
            period        CHAR(1) NOT NULL,
            period_start  DATE NOT NULL,
            count         INTEGER NOT NULL DEFAULT 0,
            updated_at    TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, quota_key, period, period_start)
        );
        CREATE INDEX IF NOT EXISTS idx_usage_counters_period
            ON usage_counters(period, period_start);
        """
    )

    # --- seed tarifs -------------------------------------------------------
    # Лимиты: day = "d", month = "m". -1 = безлимит.
    free_limits = {
        "ai_chat_msg": {"limit": 10, "period": "d"},
        "ai_photo": {"limit": 3, "period": "d"},
        "ai_meal_plan": {"limit": 1, "period": "m"},
        "ai_workout_plan": {"limit": 1, "period": "m"},
        "ai_recipe": {"limit": 3, "period": "m"},
        "ai_digest": {"limit": 1, "period": "m"},
        "food_manual": {"limit": 30, "period": "d"},
        "social_post_photo": {"limit": 0, "period": "d"},
        "history_days": {"limit": 14, "period": "static"},
    }
    premium_limits = {
        "ai_chat_msg": {"limit": 200, "period": "d"},
        "ai_photo": {"limit": 30, "period": "d"},
        "ai_meal_plan": {"limit": 10, "period": "m"},
        "ai_workout_plan": {"limit": 10, "period": "m"},
        "ai_recipe": {"limit": 30, "period": "m"},
        "ai_digest": {"limit": 8, "period": "m"},
        "food_manual": {"limit": 200, "period": "d"},
        "social_post_photo": {"limit": 1, "period": "d"},
        "history_days": {"limit": 365, "period": "static"},
    }
    pro_limits = {
        "ai_chat_msg": {"limit": -1, "period": "d"},
        "ai_photo": {"limit": -1, "period": "d"},
        "ai_meal_plan": {"limit": -1, "period": "m"},
        "ai_workout_plan": {"limit": -1, "period": "m"},
        "ai_recipe": {"limit": -1, "period": "m"},
        "ai_digest": {"limit": -1, "period": "m"},
        "food_manual": {"limit": -1, "period": "d"},
        "social_post_photo": {"limit": -1, "period": "d"},
        "history_days": {"limit": -1, "period": "static"},
    }

    plans = [
        ("free", "Free", "free", None, 0, 0, free_limits,
         ["Базовые функции", "AI-чат до 10 сообщений в день", "1 план питания в месяц"], 0),
        ("premium_month", "Premium", "premium", 30, 249, 332, premium_limits,
         ["200 AI-сообщений в день", "30 фото-анализов в день", "10 планов в месяц",
          "Дайджесты 8 раз в месяц", "История 1 год"], 10),
        ("premium_year", "Premium Year", "premium", 365, 2490, 3318, premium_limits,
         ["Все функции Premium", "−17% к месячной цене", "365 дней подряд"], 11),
        ("pro_month", "Pro", "pro", 30, 499, 665, pro_limits,
         ["Безлимитный AI-чат и фото", "Безлимитные планы и рецепты",
          "Приоритетная модель gemini-2.5-pro", "Экспорт CSV/PDF", "Без рекламы",
          "Ранний доступ к beta-фичам"], 20),
        ("pro_year", "Pro Year", "pro", 365, 4990, 6649, pro_limits,
         ["Все функции Pro", "−17% к месячной цене", "365 дней подряд"], 21),
    ]

    import json as _json
    for plan_key, name, tier, duration_days, price_stars, price_usd_cents, limits, features, sort_order in plans:
        op.execute(
            f"""
            INSERT INTO tier_plans
                (plan_key, name, tier, duration_days, price_stars, price_usd_cents,
                 limits, features, is_active, sort_order)
            VALUES
                ('{plan_key}', '{name}', '{tier}',
                 {'NULL' if duration_days is None else duration_days},
                 {price_stars}, {price_usd_cents},
                 '{_json.dumps(limits)}'::jsonb,
                 '{_json.dumps(features, ensure_ascii=False)}'::jsonb,
                 TRUE, {sort_order})
            ON CONFLICT (plan_key) DO UPDATE SET
                name            = EXCLUDED.name,
                tier            = EXCLUDED.tier,
                duration_days   = EXCLUDED.duration_days,
                price_stars     = EXCLUDED.price_stars,
                price_usd_cents = EXCLUDED.price_usd_cents,
                limits          = EXCLUDED.limits,
                features        = EXCLUDED.features,
                is_active       = TRUE,
                sort_order      = EXCLUDED.sort_order;
            """
        )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS usage_counters;
        DROP TABLE IF EXISTS star_payments;
        DROP TABLE IF EXISTS subscriptions;
        DROP TABLE IF EXISTS tier_plans;
        """
    )
