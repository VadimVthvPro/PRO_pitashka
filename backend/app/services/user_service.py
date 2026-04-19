from datetime import date
import asyncpg

from app.repositories.user_repo import UserRepository
from app.utils.calculations import calculate_age, calculate_bmi, classify_bmi, calculate_daily_calories


class UserService:
    def __init__(self, pool: asyncpg.Pool):
        self.repo = UserRepository(pool)

    async def get_profile(self, user_id: int) -> dict | None:
        user = await self.repo.get_by_id(user_id)
        if not user:
            return None
        health = await self.repo.get_health(user_id)
        aims = await self.repo.get_aims(user_id)
        lang = await self.repo.get_lang(user_id)
        return {
            **user,
            "health": health,
            "aims": aims,
            "lang": lang,
        }

    async def complete_onboarding(
        self, user_id: int,
        height: float, weight: float, date_of_birth: date, sex: str, aim: str,
    ) -> dict:
        age = calculate_age(date_of_birth)
        bmi = calculate_bmi(weight, height)
        bmi_class = classify_bmi(bmi)
        daily_cal = calculate_daily_calories(weight, height, age, sex, aim)

        await self.repo.save_onboarding(
            user_id=user_id,
            height=height, weight=weight,
            date_of_birth=date_of_birth, sex=sex, aim=aim,
            imt=bmi, imt_str=bmi_class, daily_cal=daily_cal,
        )
        return {"bmi": bmi, "bmi_class": bmi_class, "daily_cal": daily_cal}

    async def update_weight(self, user_id: int, weight: float) -> dict:
        return await self.update_profile_data(user_id, weight=weight)

    async def update_profile_data(
        self, user_id: int,
        weight: float | None = None,
        height: float | None = None,
        aim: str | None = None,
    ) -> dict:
        health = await self.repo.get_health(user_id)
        current_height = health["height"] if health else 170
        current_weight = health["weight"] if health else 70
        user = await self.repo.get_by_id(user_id)
        aims = await self.repo.get_aims(user_id)

        final_weight = weight if weight is not None else current_weight
        final_height = height if height is not None else current_height
        age = calculate_age(user["date_of_birth"]) if user and user["date_of_birth"] else 25
        sex = user["user_sex"] if user else "M"
        final_aim = aim if aim is not None else (aims["user_aim"] if aims else "maintain")

        bmi = calculate_bmi(final_weight, final_height)
        bmi_class = classify_bmi(bmi)
        daily_cal = calculate_daily_calories(final_weight, final_height, age, sex, final_aim)

        await self.repo.save_onboarding(
            user_id=user_id,
            height=final_height, weight=final_weight,
            date_of_birth=user["date_of_birth"] if user else date.today(),
            sex=sex, aim=final_aim,
            imt=bmi, imt_str=bmi_class, daily_cal=daily_cal,
        )
        return {"bmi": bmi, "bmi_class": bmi_class, "daily_cal": daily_cal, "aim": final_aim}
