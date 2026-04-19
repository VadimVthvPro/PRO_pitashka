import logging
from fastapi import APIRouter, HTTPException
from app.dependencies import DbDep, CurrentUserDep, RedisDep
from app.models.ai import ChatRequest, ChatResponse, RecipeRequest
from app.repositories.chat_repo import ChatRepository
from app.repositories.user_repo import UserRepository
from app.services import ai_service
from app.services.ai_service import (
    AIConfigError,
    AIQuotaError,
    AITimeoutError,
    AIUpstreamError,
)
from app.services.cache_service import CacheService
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _ai_http_error(exc: Exception) -> HTTPException:
    """Map an internal AI error to a clean HTTP response.

    503 + machine-readable code lets the frontend show a tailored message
    ("обновите ключ" vs "превышен лимит" vs "временный сбой"). We also set
    ``Retry-After`` for transient errors so clients can back off.
    """
    if isinstance(exc, AIConfigError):
        return HTTPException(
            status_code=503,
            detail={
                "code": "ai_misconfigured",
                "message": "AI ключ не настроен. Свяжись с администратором.",
                "hint": str(exc),
            },
        )
    if isinstance(exc, AIQuotaError):
        return HTTPException(
            status_code=429,
            detail={
                "code": "ai_quota_exceeded",
                "message": "Превышен лимит AI на сегодня. Попробуй позже.",
            },
            headers={"Retry-After": "300"},
        )
    if isinstance(exc, AITimeoutError):
        return HTTPException(
            status_code=504,
            detail={
                "code": "ai_timeout",
                "message": "AI слишком долго думает. Попробуй ещё раз.",
            },
            headers={"Retry-After": "10"},
        )
    if isinstance(exc, AIUpstreamError):
        return HTTPException(
            status_code=503,
            detail={
                "code": "ai_unavailable",
                "message": "AI временно недоступен. Попробуй ещё раз через минуту.",
            },
            headers={"Retry-After": "30"},
        )
    return HTTPException(
        status_code=503,
        detail={
            "code": "ai_unavailable",
            "message": "AI временно недоступен. Попробуй ещё раз через минуту.",
        },
        headers={"Retry-After": "30"},
    )


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(body: ChatRequest, user_id: CurrentUserDep, db: DbDep):
    chat_repo = ChatRepository(db)
    context = await chat_repo.get_context(user_id)
    user_info = await chat_repo.get_user_info_for_ai(user_id)

    user_repo = UserRepository(db)
    lang = await user_repo.get_lang(user_id)

    try:
        response_text = await ai_service.chat(body.message, context, user_info, lang)
    except Exception as e:
        logger.warning("AI chat failed: %s", e)
        raise _ai_http_error(e)

    try:
        async with db.acquire() as conn, conn.transaction():
            await conn.execute(
                "INSERT INTO chat_history (user_id, message_type, message_text) "
                "VALUES ($1, 'user', $2)",
                user_id, body.message,
            )
            await conn.execute(
                "INSERT INTO chat_history (user_id, message_type, message_text) "
                "VALUES ($1, 'assistant', $2)",
                user_id, response_text,
            )
    except Exception as e:
        logger.error("AI chat: failed to persist conversation: %s", e)

    return ChatResponse(response=response_text)


@router.post("/meal-plan")
async def generate_meal_plan(user_id: CurrentUserDep, db: DbDep, redis: RedisDep):
    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)

    cache_key = f"meal_plan:{user_id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    chat_repo = ChatRepository(db)
    user_info = await chat_repo.get_user_info_for_ai(user_id)
    user_repo = UserRepository(db)
    lang = await user_repo.get_lang(user_id)

    try:
        plan = await ai_service.generate_meal_plan(user_info, lang)
    except Exception as e:
        logger.warning("AI meal plan failed: %s", e)
        raise _ai_http_error(e)
    result = {"plan": plan}
    await cache.set(cache_key, result, settings.CACHE_TTL_RECIPES)
    return result


@router.post("/workout-plan")
async def generate_workout_plan(user_id: CurrentUserDep, db: DbDep, redis: RedisDep):
    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)

    cache_key = f"workout_plan:{user_id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    chat_repo = ChatRepository(db)
    user_info = await chat_repo.get_user_info_for_ai(user_id)
    user_repo = UserRepository(db)
    lang = await user_repo.get_lang(user_id)

    try:
        plan = await ai_service.generate_workout_plan(user_info, lang)
    except Exception as e:
        logger.warning("AI workout plan failed: %s", e)
        raise _ai_http_error(e)
    result = {"plan": plan}
    await cache.set(cache_key, result, settings.CACHE_TTL_RECIPES)
    return result


@router.post("/recipe")
async def generate_recipe(body: RecipeRequest, user_id: CurrentUserDep, db: DbDep, redis: RedisDep):
    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)

    cache_key = f"recipe:{user_id}:{body.meal_type}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    chat_repo = ChatRepository(db)
    user_info = await chat_repo.get_user_info_for_ai(user_id)
    user_repo = UserRepository(db)
    lang = await user_repo.get_lang(user_id)

    try:
        recipe = await ai_service.generate_recipe(body.meal_type, user_info, lang)
    except Exception as e:
        logger.warning("AI recipe failed: %s", e)
        raise _ai_http_error(e)
    result = {"recipe": recipe, "meal_type": body.meal_type}
    await cache.set(cache_key, result, settings.CACHE_TTL_RECIPES)
    return result
