import asyncpg
from datetime import date


class WaterRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def add_glass(self, user_id: int) -> int:
        row = await self.pool.fetchrow(
            "INSERT INTO water (user_id, date, count) VALUES ($1, CURRENT_DATE, 1) "
            "ON CONFLICT (user_id, date) DO UPDATE SET count = water.count + 1 "
            "RETURNING count",
            user_id,
        )
        return int(row["count"])

    async def get_by_date(self, user_id: int, water_date: date) -> int:
        row = await self.pool.fetchrow(
            "SELECT COALESCE(count, 0) as count FROM water WHERE user_id = $1 AND date = $2",
            user_id, water_date,
        )
        return int(row["count"]) if row else 0

    async def get_by_period(self, user_id: int, start: date, end: date) -> list[dict]:
        rows = await self.pool.fetch(
            "SELECT date, count FROM water WHERE user_id = $1 AND date BETWEEN $2 AND $3 ORDER BY date",
            user_id, start, end,
        )
        return [dict(r) for r in rows]
