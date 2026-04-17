import asyncpg
from datetime import date
from typing import Optional


class WeightRepository:
    """Reads/writes weight via user_health (one row per date)."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def history(self, user_id: int, days: int = 90) -> list[dict]:
        rows = await self.pool.fetch(
            """
            SELECT date, weight
            FROM user_health
            WHERE user_id = $1
              AND weight IS NOT NULL
              AND weight > 0
              AND date >= CURRENT_DATE - ($2::int - 1) * INTERVAL '1 day'
            ORDER BY date
            """,
            user_id, days,
        )
        return [{"date": r["date"].isoformat(), "weight": float(r["weight"])} for r in rows]

    async def latest(self, user_id: int) -> Optional[dict]:
        row = await self.pool.fetchrow(
            """
            SELECT date, weight, height
            FROM user_health
            WHERE user_id = $1 AND weight IS NOT NULL AND weight > 0
            ORDER BY date DESC
            LIMIT 1
            """,
            user_id,
        )
        return dict(row) if row else None

    async def add_or_update(self, user_id: int, weight: float) -> dict:
        """Upsert weight for today. Carries over height from latest row."""
        latest = await self.latest(user_id)
        height = float(latest["height"]) if latest and latest.get("height") else 170.0
        height_m = height / 100 if height > 3 else height
        imt = round(weight / (height_m * height_m), 1)

        row = await self.pool.fetchrow(
            """
            INSERT INTO user_health (user_id, imt, imt_str, cal, date, weight, height)
            VALUES ($1, $2, '', 0, CURRENT_DATE, $3, $4)
            RETURNING date, weight, imt
            """,
            user_id, imt, weight, height,
        )
        return {"date": row["date"].isoformat(), "weight": float(row["weight"]), "imt": float(row["imt"])}

    async def target_weight(self, user_id: int) -> Optional[float]:
        """Compute target weight from user's goal (weight_loss / gain / maintain)."""
        row = await self.pool.fetchrow(
            """
            SELECT user_aim FROM user_aims WHERE user_id = $1
            """,
            user_id,
        )
        if not row:
            return None
        aim = (row["user_aim"] or "").lower()
        latest = await self.latest(user_id)
        if not latest:
            return None
        current = float(latest["weight"])
        height = float(latest["height"] or 170) / 100
        if height <= 0 or height > 3:
            height = 1.7 if height <= 0 else height / 100

        healthy_bmi_low, healthy_bmi_high = 20.0, 25.0
        if "loss" in aim or "похуд" in aim or "сброс" in aim:
            return round(height * height * healthy_bmi_low, 1)
        if "gain" in aim or "набор" in aim:
            return round(current + 5.0, 1)
        return round(current, 1)
