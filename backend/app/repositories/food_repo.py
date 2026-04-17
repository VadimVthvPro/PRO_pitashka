import asyncpg
from datetime import date


class FoodRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def add(
        self, user_id: int, food_date: date, name: str,
        protein: float, fat: float, carbs: float, calories: float,
    ) -> dict:
        row = await self.pool.fetchrow(
            "INSERT INTO food (user_id, date, name_of_food, b, g, u, cal) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *",
            user_id, food_date, name, protein, fat, carbs, calories,
        )
        return dict(row)

    async def get_by_date(self, user_id: int, food_date: date) -> list[dict]:
        rows = await self.pool.fetch(
            "SELECT name_of_food, b, g, u, cal FROM food "
            "WHERE user_id = $1 AND date = $2 ORDER BY id",
            user_id, food_date,
        )
        return [dict(r) for r in rows]

    async def get_daily_totals(self, user_id: int, food_date: date) -> dict:
        row = await self.pool.fetchrow(
            "SELECT COALESCE(SUM(cal), 0) as total_cal, "
            "COALESCE(SUM(b), 0) as total_protein, "
            "COALESCE(SUM(g), 0) as total_fat, "
            "COALESCE(SUM(u), 0) as total_carbs "
            "FROM food WHERE user_id = $1 AND date = $2",
            user_id, food_date,
        )
        return dict(row)
