import asyncpg
from datetime import date


class UserRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_by_id(self, user_id: int) -> dict | None:
        row = await self.pool.fetchrow(
            "SELECT user_id, user_name, user_sex, date_of_birth FROM user_main WHERE user_id = $1",
            user_id,
        )
        return dict(row) if row else None

    async def get_health(self, user_id: int) -> dict | None:
        row = await self.pool.fetchrow(
            "SELECT imt, imt_str, cal, weight, height, date FROM user_health "
            "WHERE user_id = $1 ORDER BY date DESC LIMIT 1",
            user_id,
        )
        return dict(row) if row else None

    async def get_aims(self, user_id: int) -> dict | None:
        row = await self.pool.fetchrow(
            "SELECT user_aim, daily_cal FROM user_aims WHERE user_id = $1",
            user_id,
        )
        return dict(row) if row else None

    async def get_lang(self, user_id: int) -> str:
        row = await self.pool.fetchrow(
            "SELECT lang FROM user_lang WHERE user_id = $1", user_id
        )
        return row["lang"] if row else "ru"

    async def set_lang(self, user_id: int, lang: str) -> None:
        await self.pool.execute(
            "INSERT INTO user_lang (user_id, lang) VALUES ($1, $2) "
            "ON CONFLICT (user_id) DO UPDATE SET lang = $2",
            user_id, lang,
        )

    async def save_onboarding(
        self,
        user_id: int,
        height: float,
        weight: float,
        date_of_birth: date,
        sex: str,
        aim: str,
        imt: float,
        imt_str: str,
        daily_cal: float,
    ) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE user_main SET user_sex = $2, date_of_birth = $3 WHERE user_id = $1",
                    user_id, sex, date_of_birth,
                )
                await conn.execute(
                    "INSERT INTO user_health (user_id, imt, imt_str, cal, date, weight, height) "
                    "VALUES ($1, $2, $3, $4, CURRENT_DATE, $5, $6)",
                    user_id, imt, imt_str, daily_cal, weight, height,
                )
                await conn.execute(
                    "INSERT INTO user_aims (user_id, user_aim, daily_cal) VALUES ($1, $2, $3) "
                    "ON CONFLICT (user_id) DO UPDATE SET user_aim = $2, daily_cal = $3",
                    user_id, aim, daily_cal,
                )

    async def update_profile(self, user_id: int, weight: float | None = None, height: float | None = None) -> None:
        if weight is not None and height is not None:
            await self.pool.execute(
                "INSERT INTO user_health (user_id, imt, imt_str, cal, date, weight, height) "
                "VALUES ($1, 0, '', 0, CURRENT_DATE, $2, $3)",
                user_id, weight, height,
            )

    async def get_privacy_consent(self, user_id: int) -> bool:
        row = await self.pool.fetchrow(
            "SELECT privacy_consent_given FROM user_main WHERE user_id = $1", user_id
        )
        return row["privacy_consent_given"] if row else False

    async def get_settings(self, user_id: int) -> dict | None:
        row = await self.pool.fetchrow(
            "SELECT theme, notifications_enabled FROM user_settings WHERE user_id = $1", user_id
        )
        return dict(row) if row else {"theme": "auto", "notifications_enabled": True}

    async def update_settings(self, user_id: int, theme: str | None = None, notifications: bool | None = None) -> None:
        await self.pool.execute(
            "INSERT INTO user_settings (user_id, theme, notifications_enabled) "
            "VALUES ($1, COALESCE($2, 'auto'), COALESCE($3, TRUE)) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "theme = COALESCE($2, user_settings.theme), "
            "notifications_enabled = COALESCE($3, user_settings.notifications_enabled), "
            "updated_at = NOW()",
            user_id, theme, notifications,
        )
