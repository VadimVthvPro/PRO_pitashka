from fastapi import APIRouter
from app.dependencies import DbDep, CurrentUserDep
from app.models.user import OnboardingRequest, OnboardingResponse, ProfileResponse, UpdateProfileRequest
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me/account")
async def get_account(user_id: CurrentUserDep, db: DbDep):
    """Summary of linked auth-providers for the settings page.

    Возвращает, через какие способы пользователь может войти в свой
    аккаунт: Telegram (если есть `telegram_username`), Google, Yandex, VK.
    UI использует эти флаги чтобы показать «Привязано» / «Привязать»
    для каждого провайдера и правильно подписать кнопку «Выйти».
    """
    row = await db.fetchrow(
        """
        SELECT
            user_id,
            display_name,
            user_name,
            telegram_username,
            google_email,
            google_picture,
            google_linked_at,
            yandex_email,
            yandex_login,
            yandex_avatar_id,
            yandex_linked_at
        FROM user_main
        WHERE user_id = $1
        """,
        user_id,
    )
    if not row:
        return {
            "user_id": user_id,
            "display_name": None,
            "providers": {
                "telegram": {"linked": False},
                "google": {"linked": False},
                "yandex": {"linked": False},
            },
        }

    # Telegram «linked» определяем по наличию telegram_username, потому
    # что после миграции 017 user_id ≠ обязательно Telegram id: у
    # Google/Yandex/VK-only юзеров user_id синтетический (>= 10^13).
    tg_linked = bool(row["telegram_username"])

    return {
        "user_id": row["user_id"],
        "display_name": row["display_name"] or row["user_name"],
        "providers": {
            "telegram": {
                "linked": tg_linked,
                "username": row["telegram_username"],
            },
            "google": {
                "linked": row["google_linked_at"] is not None,
                "email": row["google_email"],
                "picture": row["google_picture"],
            },
            "yandex": {
                "linked": row["yandex_linked_at"] is not None,
                "email": row["yandex_email"],
                "login": row["yandex_login"],
                "avatar_id": row["yandex_avatar_id"],
            },
        },
    }


@router.get("/me", response_model=ProfileResponse)
async def get_profile(user_id: CurrentUserDep, db: DbDep):
    svc = UserService(db)
    profile = await svc.get_profile(user_id)
    if not profile:
        return ProfileResponse(user_id=user_id)

    health = profile.get("health") or {}
    aims = profile.get("aims") or {}
    return ProfileResponse(
        user_id=profile["user_id"],
        user_name=profile.get("user_name"),
        user_sex=profile.get("user_sex"),
        date_of_birth=profile.get("date_of_birth"),
        weight=health.get("weight"),
        height=health.get("height"),
        bmi=health.get("imt"),
        bmi_class=health.get("imt_str"),
        daily_cal=aims.get("daily_cal"),
        aim=aims.get("user_aim"),
        lang=profile.get("lang", "ru"),
    )


@router.post("/onboarding", response_model=OnboardingResponse)
async def onboarding(body: OnboardingRequest, user_id: CurrentUserDep, db: DbDep):
    svc = UserService(db)
    result = await svc.complete_onboarding(
        user_id=user_id,
        height=body.height, weight=body.weight,
        date_of_birth=body.date_of_birth,
        sex=body.sex, aim=body.aim,
    )
    return OnboardingResponse(**result)


@router.put("/me")
async def update_profile(body: UpdateProfileRequest, user_id: CurrentUserDep, db: DbDep):
    svc = UserService(db)
    if body.weight is not None or body.height is not None or body.aim is not None:
        return await svc.update_profile_data(
            user_id,
            weight=body.weight,
            height=body.height,
            aim=body.aim,
        )
    return {"message": "No changes"}
