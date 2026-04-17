import asyncpg


class ChatRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def save_message(self, user_id: int, message_type: str, text: str) -> None:
        await self.pool.execute(
            "INSERT INTO chat_history (user_id, message_type, message_text) VALUES ($1, $2, $3)",
            user_id, message_type, text,
        )

    async def get_context(self, user_id: int, limit: int = 10) -> list[dict]:
        rows = await self.pool.fetch(
            "SELECT message_type, message_text, created_at FROM chat_history "
            "WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
            user_id, limit,
        )
        return [dict(r) for r in reversed(rows)]

    async def get_user_info_for_ai(self, user_id: int) -> dict:
        user = await self.pool.fetchrow(
            "SELECT user_sex, date_of_birth FROM user_main WHERE user_id = $1", user_id
        )
        health = await self.pool.fetchrow(
            "SELECT imt, weight, height FROM user_health WHERE user_id = $1 ORDER BY date DESC LIMIT 1", user_id
        )
        aims = await self.pool.fetchrow(
            "SELECT user_aim, daily_cal FROM user_aims WHERE user_id = $1", user_id
        )
        return {
            "sex": user["user_sex"] if user else None,
            "date_of_birth": user["date_of_birth"].isoformat() if user and user["date_of_birth"] else None,
            "imt": float(health["imt"]) if health else None,
            "weight": float(health["weight"]) if health else None,
            "height": float(health["height"]) if health else None,
            "aim": aims["user_aim"] if aims else None,
            "daily_cal": float(aims["daily_cal"]) if aims else None,
        }
