import asyncpg
from datetime import date


class WorkoutRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_training_types(self, lang: str = "ru") -> list[dict]:
        name_col = f"name_{lang}" if lang in ("ru", "en", "de", "fr", "es") else "name_ru"
        desc_col = f"description_{lang}" if lang in ("ru", "en", "de", "fr", "es") else "description_ru"
        rows = await self.pool.fetch(
            f"SELECT id, {name_col} as name, emoji, {desc_col} as description, base_coefficient "
            f"FROM training_types WHERE is_active = true ORDER BY id",
        )
        return [dict(r) for r in rows]

    async def get_training_by_id(self, training_id: int) -> dict | None:
        row = await self.pool.fetchrow(
            "SELECT id, name_ru, emoji, base_coefficient FROM training_types WHERE id = $1",
            training_id,
        )
        return dict(row) if row else None

    async def calculate_calories(self, training_type_id: int, duration_minutes: int, user_id: int) -> float:
        row = await self.pool.fetchrow(
            "SELECT calculate_training_calories($1, $2, $3) as calories",
            user_id, training_type_id, duration_minutes,
        )
        return float(row["calories"]) if row and row["calories"] else 0.0

    async def save(
        self, user_id: int, training_type_id: int, training_name: str,
        workout_date: date, duration: int, calories: float,
    ) -> dict:
        row = await self.pool.fetchrow(
            "INSERT INTO user_training (user_id, training_type_id, training_name, date, tren_time, training_cal) "
            "VALUES ($1, $2, $3, $4, $5, $6) RETURNING *",
            user_id, training_type_id, training_name, workout_date, duration, calories,
        )
        return dict(row)

    async def get_total_calories(self, user_id: int, target_date: date | None = None) -> float:
        d = target_date or date.today()
        row = await self.pool.fetchrow(
            "SELECT COALESCE(SUM(training_cal), 0) as total "
            "FROM user_training WHERE user_id = $1 AND date = $2",
            user_id, d,
        )
        return float(row["total"])

    async def get_total_duration(self, user_id: int, target_date: date | None = None) -> int:
        d = target_date or date.today()
        row = await self.pool.fetchrow(
            "SELECT COALESCE(SUM(tren_time), 0) as total "
            "FROM user_training WHERE user_id = $1 AND date = $2",
            user_id, d,
        )
        return int(row["total"])

    async def get_by_date(self, user_id: int, workout_date: date) -> list[dict]:
        rows = await self.pool.fetch(
            "SELECT training_name, tren_time, training_cal FROM user_training "
            "WHERE user_id = $1 AND date = $2 ORDER BY id",
            user_id, workout_date,
        )
        return [dict(r) for r in rows]

    async def get_by_period(self, user_id: int, start: date, end: date) -> list[dict]:
        rows = await self.pool.fetch(
            "SELECT training_name, date, tren_time, training_cal FROM user_training "
            "WHERE user_id = $1 AND date BETWEEN $2 AND $3 ORDER BY date",
            user_id, start, end,
        )
        return [dict(r) for r in rows]

    async def get_top5_period(self, user_id: int, start: date, end: date) -> list[dict]:
        rows = await self.pool.fetch(
            "SELECT training_name, COUNT(*) as cnt, SUM(training_cal) as total_cal "
            "FROM user_training WHERE user_id = $1 AND date BETWEEN $2 AND $3 "
            "GROUP BY training_name ORDER BY total_cal DESC LIMIT 5",
            user_id, start, end,
        )
        return [dict(r) for r in rows]
