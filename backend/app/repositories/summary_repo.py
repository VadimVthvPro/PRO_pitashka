import asyncpg
from datetime import date


class SummaryRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_day(self, user_id: int, day: date) -> dict:
        food = await self.pool.fetchrow(
            "SELECT COALESCE(SUM(cal), 0) as cal, COALESCE(SUM(b), 0) as protein, "
            "COALESCE(SUM(g), 0) as fat, COALESCE(SUM(u), 0) as carbs "
            "FROM food WHERE user_id = $1 AND date = $2",
            user_id, day,
        )
        food_items = await self.pool.fetch(
            "SELECT name_of_food, b, g, u, cal FROM food WHERE user_id = $1 AND date = $2",
            user_id, day,
        )
        training = await self.pool.fetchrow(
            "SELECT COALESCE(SUM(training_cal), 0) as cal, COALESCE(SUM(tren_time), 0) as duration "
            "FROM user_training WHERE user_id = $1 AND date = $2",
            user_id, day,
        )
        training_items = await self.pool.fetch(
            "SELECT training_name, tren_time, training_cal FROM user_training WHERE user_id = $1 AND date = $2",
            user_id, day,
        )
        water = await self.pool.fetchrow(
            "SELECT COALESCE(count, 0) as count FROM water WHERE user_id = $1 AND date = $2",
            user_id, day,
        )
        weight = await self.pool.fetchrow(
            "SELECT weight FROM user_health WHERE user_id = $1 AND date = $2",
            user_id, day,
        )
        return {
            "date": day.isoformat(),
            "food": dict(food),
            "food_items": [dict(r) for r in food_items],
            "training": dict(training),
            "training_items": [dict(r) for r in training_items],
            "water": water["count"] if water else 0,
            "weight": float(weight["weight"]) if weight else None,
        }

    async def get_month(self, user_id: int, year: int, month: int) -> dict:
        food = await self.pool.fetchrow(
            "SELECT COALESCE(SUM(cal), 0) as cal, COALESCE(SUM(b), 0) as protein, "
            "COALESCE(SUM(g), 0) as fat, COALESCE(SUM(u), 0) as carbs, "
            "COUNT(DISTINCT date) as days "
            "FROM food WHERE user_id = $1 AND EXTRACT(YEAR FROM date) = $2 AND EXTRACT(MONTH FROM date) = $3",
            user_id, year, month,
        )
        training = await self.pool.fetchrow(
            "SELECT COALESCE(SUM(training_cal), 0) as cal, COALESCE(SUM(tren_time), 0) as duration, "
            "COUNT(*) as count "
            "FROM user_training WHERE user_id = $1 AND EXTRACT(YEAR FROM date) = $2 AND EXTRACT(MONTH FROM date) = $3",
            user_id, year, month,
        )
        water = await self.pool.fetchrow(
            "SELECT COALESCE(SUM(count), 0) as total FROM water "
            "WHERE user_id = $1 AND EXTRACT(YEAR FROM date) = $2 AND EXTRACT(MONTH FROM date) = $3",
            user_id, year, month,
        )
        top5 = await self.pool.fetch(
            "SELECT training_name, COUNT(*) as cnt, SUM(training_cal) as total_cal "
            "FROM user_training WHERE user_id = $1 AND EXTRACT(YEAR FROM date) = $2 AND EXTRACT(MONTH FROM date) = $3 "
            "GROUP BY training_name ORDER BY total_cal DESC LIMIT 5",
            user_id, year, month,
        )
        weights = await self.pool.fetch(
            "SELECT date, weight FROM user_health "
            "WHERE user_id = $1 AND EXTRACT(YEAR FROM date) = $2 AND EXTRACT(MONTH FROM date) = $3 "
            "ORDER BY date",
            user_id, year, month,
        )
        return {
            "year": year, "month": month,
            "food": dict(food),
            "training": dict(training),
            "water_total": water["total"] if water else 0,
            "top5_training": [dict(r) for r in top5],
            "weights": [{"date": r["date"].isoformat(), "weight": float(r["weight"])} for r in weights],
        }

    async def get_year(self, user_id: int, year: int) -> dict:
        food = await self.pool.fetchrow(
            "SELECT COALESCE(SUM(cal), 0) as cal, COALESCE(SUM(b), 0) as protein, "
            "COALESCE(SUM(g), 0) as fat, COALESCE(SUM(u), 0) as carbs "
            "FROM food WHERE user_id = $1 AND EXTRACT(YEAR FROM date) = $2",
            user_id, year,
        )
        monthly_food = await self.pool.fetch(
            "SELECT EXTRACT(MONTH FROM date)::int as month, "
            "SUM(cal) as cal, SUM(b) as protein, SUM(g) as fat, SUM(u) as carbs "
            "FROM food WHERE user_id = $1 AND EXTRACT(YEAR FROM date) = $2 "
            "GROUP BY EXTRACT(MONTH FROM date) ORDER BY month",
            user_id, year,
        )
        training = await self.pool.fetchrow(
            "SELECT COALESCE(SUM(training_cal), 0) as cal, COALESCE(SUM(tren_time), 0) as duration "
            "FROM user_training WHERE user_id = $1 AND EXTRACT(YEAR FROM date) = $2",
            user_id, year,
        )
        top5 = await self.pool.fetch(
            "SELECT training_name, COUNT(*) as cnt, SUM(training_cal) as total_cal "
            "FROM user_training WHERE user_id = $1 AND EXTRACT(YEAR FROM date) = $2 "
            "GROUP BY training_name ORDER BY total_cal DESC LIMIT 5",
            user_id, year,
        )
        water = await self.pool.fetchrow(
            "SELECT COALESCE(SUM(count), 0) as total FROM water "
            "WHERE user_id = $1 AND EXTRACT(YEAR FROM date) = $2",
            user_id, year,
        )
        return {
            "year": year,
            "food": dict(food),
            "monthly_food": [dict(r) for r in monthly_food],
            "training": dict(training),
            "top5_training": [dict(r) for r in top5],
            "water_total": water["total"] if water else 0,
        }
