from fastapi import APIRouter
from app.dependencies import DbDep, CurrentUserDep
from app.models.user import SettingsRequest
from app.repositories.user_repo import UserRepository

router = APIRouter()


@router.get("")
async def get_settings_endpoint(user_id: CurrentUserDep, db: DbDep):
    repo = UserRepository(db)
    user_settings = await repo.get_settings(user_id)
    lang = await repo.get_lang(user_id)
    theme = user_settings.get("theme", "auto") if user_settings else "auto"
    notif = user_settings.get("notifications_enabled", True) if user_settings else True
    return {
        "theme": theme,
        "notifications": notif,
        "language": lang or "ru",
    }


@router.put("")
async def update_settings(body: SettingsRequest, user_id: CurrentUserDep, db: DbDep):
    repo = UserRepository(db)
    if body.language:
        await repo.set_lang(user_id, body.language)
    if body.theme is not None or body.notifications is not None:
        await repo.update_settings(user_id, body.theme, body.notifications)
    return {"message": "Settings updated"}
