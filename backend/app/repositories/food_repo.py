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

    async def get_favorites(self, user_id: int, limit: int = 12) -> list[dict]:
        """Most frequently logged unique foods with average macros."""
        rows = await self.pool.fetch(
            """
            SELECT
                name_of_food AS name,
                COUNT(*) AS times,
                AVG(b)::numeric(10, 2) AS b,
                AVG(g)::numeric(10, 2) AS g,
                AVG(u)::numeric(10, 2) AS u,
                AVG(cal)::numeric(10, 2) AS cal,
                MAX(date) AS last_date
            FROM food
            WHERE user_id = $1
            GROUP BY name_of_food
            ORDER BY COUNT(*) DESC, MAX(date) DESC
            LIMIT $2
            """,
            user_id, limit,
        )
        return [dict(r) for r in rows]

    async def get_last_day_with_food(self, user_id: int, before: date) -> date | None:
        """Most recent date strictly before `before` that has at least one food entry."""
        row = await self.pool.fetchrow(
            "SELECT MAX(date) AS last_date FROM food WHERE user_id = $1 AND date < $2",
            user_id, before,
        )
        return row["last_date"] if row and row["last_date"] else None

    async def copy_day(
        self, user_id: int, source_date: date, target_date: date
    ) -> int:
        """Copy all entries from source_date to target_date. Returns number copied."""
        row = await self.pool.fetchrow(
            """
            WITH inserted AS (
              INSERT INTO food (user_id, date, name_of_food, b, g, u, cal)
              SELECT user_id, $3, name_of_food, b, g, u, cal
              FROM food
              WHERE user_id = $1 AND date = $2
              RETURNING 1
            )
            SELECT COUNT(*) AS c FROM inserted
            """,
            user_id, source_date, target_date,
        )
        return int(row["c"]) if row else 0
