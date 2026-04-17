import asyncpg
from datetime import date
from typing import Optional


class StreakRepository:
    """DB access for user_streaks, badges, user_badges."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    # ---------- streaks ----------

    async def get_streak(self, user_id: int) -> Optional[dict]:
        row = await self.pool.fetchrow(
            "SELECT user_id, current_streak, longest_streak, last_active_date, "
            "       freezes_available, last_freeze_reset "
            "FROM user_streaks WHERE user_id = $1",
            user_id,
        )
        return dict(row) if row else None

    async def upsert_streak(
        self,
        user_id: int,
        current: int,
        longest: int,
        last_active: date,
        freezes: int,
        last_freeze_reset: Optional[date],
    ) -> None:
        await self.pool.execute(
            """
            INSERT INTO user_streaks
                (user_id, current_streak, longest_streak, last_active_date,
                 freezes_available, last_freeze_reset, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                current_streak = EXCLUDED.current_streak,
                longest_streak = EXCLUDED.longest_streak,
                last_active_date = EXCLUDED.last_active_date,
                freezes_available = EXCLUDED.freezes_available,
                last_freeze_reset = EXCLUDED.last_freeze_reset,
                updated_at = NOW()
            """,
            user_id, current, longest, last_active, freezes, last_freeze_reset,
        )

    # ---------- activity counts (for badge evaluation) ----------

    async def food_entries_count(self, user_id: int) -> int:
        row = await self.pool.fetchrow(
            "SELECT COUNT(*) AS c FROM food WHERE user_id = $1",
            user_id,
        )
        return int(row["c"]) if row else 0

    async def water_goal_streak(self, user_id: int, target: int = 8) -> int:
        """Count consecutive days ending today where water.count >= target."""
        row = await self.pool.fetchrow(
            """
            WITH days AS (
              SELECT date, count
              FROM water
              WHERE user_id = $1 AND count >= $2
                AND date <= CURRENT_DATE
              ORDER BY date DESC
              LIMIT 60
            ),
            numbered AS (
              SELECT date,
                     CURRENT_DATE - ROW_NUMBER() OVER (ORDER BY date DESC)::int AS expected
              FROM days
            )
            SELECT COUNT(*)::int AS streak
            FROM numbered
            WHERE date = expected + 1
            """,
            user_id, target,
        )
        return int(row["streak"]) if row else 0

    async def workouts_in_week(self, user_id: int, week_start: date) -> int:
        row = await self.pool.fetchrow(
            """
            SELECT COUNT(*) AS c
            FROM user_training
            WHERE user_id = $1
              AND date >= $2
              AND date < $2 + INTERVAL '7 days'
            """,
            user_id, week_start,
        )
        return int(row["c"]) if row else 0

    async def workouts_count(self, user_id: int) -> int:
        row = await self.pool.fetchrow(
            "SELECT COUNT(*) AS c FROM user_training WHERE user_id = $1",
            user_id,
        )
        return int(row["c"]) if row else 0

    async def water_count_total(self, user_id: int) -> int:
        row = await self.pool.fetchrow(
            "SELECT COALESCE(SUM(count), 0) AS c FROM water WHERE user_id = $1",
            user_id,
        )
        return int(row["c"]) if row else 0

    async def water_today(self, user_id: int) -> int:
        row = await self.pool.fetchrow(
            "SELECT COALESCE(count, 0) AS c FROM water "
            "WHERE user_id = $1 AND date = CURRENT_DATE",
            user_id,
        )
        return int(row["c"]) if row else 0

    async def food_totals_today(self, user_id: int) -> Optional[dict]:
        """Return dict(protein, fat, carbs, calories) for today."""
        row = await self.pool.fetchrow(
            """
            SELECT
              COALESCE(SUM(b), 0) AS protein,
              COALESCE(SUM(g), 0) AS fat,
              COALESCE(SUM(u), 0) AS carbs,
              COALESCE(SUM(cal), 0) AS calories
            FROM food
            WHERE user_id = $1 AND date = CURRENT_DATE
            """,
            user_id,
        )
        return dict(row) if row else None

    async def user_daily_cal(self, user_id: int) -> Optional[int]:
        row = await self.pool.fetchrow(
            "SELECT daily_cal FROM user_aims WHERE user_id = $1",
            user_id,
        )
        if not row:
            return None
        val = row["daily_cal"]
        return int(val) if val else None

    # ---------- badges ----------

    async def list_badges(self) -> list[dict]:
        rows = await self.pool.fetch(
            "SELECT id, code, title, description, icon, tier, category "
            "FROM badges ORDER BY sort_order"
        )
        return [dict(r) for r in rows]

    async def user_earned(self, user_id: int) -> list[dict]:
        rows = await self.pool.fetch(
            """
            SELECT b.id, b.code, b.title, b.description, b.icon, b.tier, b.category,
                   ub.earned_at
            FROM user_badges ub
            JOIN badges b ON b.id = ub.badge_id
            WHERE ub.user_id = $1
            ORDER BY ub.earned_at DESC
            """,
            user_id,
        )
        return [dict(r) for r in rows]

    async def earned_codes(self, user_id: int) -> set[str]:
        rows = await self.pool.fetch(
            "SELECT b.code FROM user_badges ub JOIN badges b ON b.id = ub.badge_id "
            "WHERE ub.user_id = $1",
            user_id,
        )
        return {r["code"] for r in rows}

    async def grant_badge(self, user_id: int, code: str) -> Optional[dict]:
        """Atomically grant a badge. Returns the badge dict if newly granted, else None."""
        row = await self.pool.fetchrow(
            """
            WITH b AS (SELECT id FROM badges WHERE code = $2),
            inserted AS (
              INSERT INTO user_badges (user_id, badge_id)
              SELECT $1, id FROM b
              ON CONFLICT (user_id, badge_id) DO NOTHING
              RETURNING badge_id, earned_at
            )
            SELECT b.id, b.code, b.title, b.description, b.icon, b.tier, b.category,
                   inserted.earned_at
            FROM inserted
            JOIN badges b ON b.id = inserted.badge_id
            """,
            user_id, code,
        )
        return dict(row) if row else None
