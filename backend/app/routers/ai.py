from fastapi import APIRouter
from app.dependencies import DbDep, CurrentUserDep, RedisDep
from app.models.ai import ChatRequest, ChatResponse, RecipeRequest
from app.repositories.chat_repo import ChatRepository
from app.repositories.user_repo import UserRepository
from app.services import ai_service
from app.services.cache_service import CacheService
from app.config import get_settings

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(body: ChatRequest, user_id: CurrentUserDep, db: DbDep):
    chat_repo = ChatRepository(db)
    context = await chat_repo.get_context(user_id)
    user_info = await chat_repo.get_user_info_for_ai(user_id)

    user_repo = UserRepository(db)
    lang = await user_repo.get_lang(user_id)

    await chat_repo.save_message(user_id, "user", body.message)
    response_text = await ai_service.chat(body.message, context, user_info, lang)
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

    plan = await ai_service.generate_meal_plan(user_info, lang)
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

    plan = await ai_service.generate_workout_plan(user_info, lang)
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

    recipe = await ai_service.generate_recipe(body.meal_type, user_info, lang)
    result = {"recipe": recipe, "meal_type": body.meal_type}
    await cache.set(cache_key, result, settings.CACHE_TTL_RECIPES)
    return result
