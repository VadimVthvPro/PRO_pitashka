import logging
from fastapi import APIRouter, HTTPException
from app.dependencies import DbDep, CurrentUserDep, RedisDep
from app.models.ai import ChatRequest, ChatResponse, RecipeRequest
from app.repositories.chat_repo import ChatRepository
from app.repositories.user_repo import UserRepository
from app.services import ai_service
from app.services.cache_service import CacheService
from app.config import get_settings

logger = logging.getLogger(__name__)
AI_UNAVAILABLE = "AI-сервис временно недоступен. Превышен лимит запросов. Попробуйте позже."

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(body: ChatRequest, user_id: CurrentUserDep, db: DbDep):
    chat_repo = ChatRepository(db)
    context = await chat_repo.get_context(user_id)
    user_info = await chat_repo.get_user_info_for_ai(user_id)

    user_repo = UserRepository(db)
    lang = await user_repo.get_lang(user_id)

    await chat_repo.save_message(user_id, "user", body.message)
    try:
        response_text = await ai_service.chat(body.message, context, user_info, lang)
    except Exception as e:
        logger.warning("AI chat failed: %s", e)
        raise HTTPException(status_code=503, detail=AI_UNAVAILABLE)
    await chat_repo.save_message(user_id, "assistant", response_text)

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
        raise HTTPException(status_code=503, detail=AI_UNAVAILABLE)
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
        raise HTTPException(status_code=503, detail=AI_UNAVAILABLE)
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
        raise HTTPException(status_code=503, detail=AI_UNAVAILABLE)
    result = {"recipe": recipe, "meal_type": body.meal_type}
    await cache.set(cache_key, result, settings.CACHE_TTL_RECIPES)
    return result
