import logging
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.dependencies import CurrentUserDep, DbDep, RedisDep
from app.models.ai import (
    ChatRequest,
    ChatResponse,
    HistoryMessage,
    HistoryResponse,
    RecipeRequest,
)
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

logger = logging.getLogger(__name__)

router = APIRouter()


def _ai_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AIConfigError):
        return HTTPException(
            status_code=503,
            detail={"code": "ai_misconfigured",
                    "message": "AI ключ не настроен. Свяжись с администратором.",
                    "hint": str(exc)},
        )
    if isinstance(exc, AIQuotaError):
        return HTTPException(
            status_code=429,
            detail={"code": "ai_quota_exceeded",
                    "message": "Превышен лимит AI на сегодня. Попробуй позже."},
            headers={"Retry-After": "300"},
        )
    if isinstance(exc, AITimeoutError):
        return HTTPException(
            status_code=504,
            detail={"code": "ai_timeout",
                    "message": "AI слишком долго думает. Попробуй ещё раз."},
            headers={"Retry-After": "10"},
        )
    if isinstance(exc, AIUpstreamError):
        return HTTPException(
            status_code=503,
            detail={"code": "ai_unavailable",
                    "message": "AI временно недоступен. Попробуй ещё раз через минуту."},
            headers={"Retry-After": "30"},
        )
    return HTTPException(
        status_code=503,
        detail={"code": "ai_unavailable",
                "message": "AI временно недоступен. Попробуй ещё раз через минуту."},
        headers={"Retry-After": "30"},
    )


# ---------------------------------------------------------------------------
# Context helpers
# ---------------------------------------------------------------------------


async def _today_snapshot(db, user_id: int) -> dict:
    """Lightweight 'what did the user log today' summary for chat context."""
    today = date.today()
    food = await db.fetchrow(
        """
        SELECT COALESCE(SUM(cal), 0) AS cal,
               COALESCE(SUM(b), 0)   AS protein,
               COALESCE(SUM(g), 0)   AS fat,
               COALESCE(SUM(u), 0)   AS carbs,
               COUNT(*)              AS items
        FROM food WHERE user_id = $1 AND date = $2
        """,
        user_id, today,
    )
    water_count = await db.fetchval(
        "SELECT COALESCE(SUM(count), 0) FROM water WHERE user_id = $1 AND date = $2",
        user_id, today,
    )
    workout = await db.fetchrow(
        """
        SELECT COALESCE(SUM(training_cal), 0) AS burned,
               COALESCE(SUM(tren_time), 0)    AS minutes,
               COUNT(*)                       AS sessions
        FROM user_training WHERE user_id = $1 AND date = $2
        """,
        user_id, today,
    )
    return {
        "date": today.isoformat(),
        "calories_in": int(food["cal"] or 0),
        "protein_g": float(food["protein"] or 0),
        "fat_g": float(food["fat"] or 0),
        "carbs_g": float(food["carbs"] or 0),
        "food_items_logged": int(food["items"] or 0),
        "water_glasses": int(water_count or 0),
        "water_ml_estimate": int((water_count or 0) * 250),
        "calories_burned": int(workout["burned"] or 0),
        "active_minutes": int(workout["minutes"] or 0),
        "workout_sessions": int(workout["sessions"] or 0),
    }


async def _week_snapshot(db, user_id: int) -> dict:
    today = date.today()
    week_ago = today - timedelta(days=6)
    food = await db.fetchrow(
        """
        SELECT COALESCE(SUM(daily_cal), 0) AS total_cal,
               COALESCE(AVG(daily_cal), 0) AS avg_cal,
               COUNT(*)                    AS days_logged
        FROM (
          SELECT date, SUM(cal) AS daily_cal
          FROM food
          WHERE user_id = $1 AND date BETWEEN $2 AND $3
          GROUP BY date
        ) AS d
        """,
        user_id, week_ago, today,
    )
    water_count = await db.fetchval(
        "SELECT COALESCE(SUM(count), 0) FROM water "
        "WHERE user_id = $1 AND date BETWEEN $2 AND $3",
        user_id, week_ago, today,
    )
    workout = await db.fetchrow(
        """
        SELECT COUNT(*)                       AS sessions,
               COALESCE(SUM(training_cal), 0) AS burned,
               COALESCE(SUM(tren_time), 0)    AS minutes
        FROM user_training
        WHERE user_id = $1 AND date BETWEEN $2 AND $3
        """,
        user_id, week_ago, today,
    )
    weight = await db.fetchrow(
        """
        SELECT weight, date FROM user_health
        WHERE user_id = $1 AND date BETWEEN $2 AND $3
        ORDER BY date DESC LIMIT 1
        """,
        user_id, week_ago, today,
    )
    return {
        "from": week_ago.isoformat(),
        "to": today.isoformat(),
        "calories_in_total": int(food["total_cal"] or 0),
        "calories_in_avg_per_day": int(food["avg_cal"] or 0),
        "days_with_food_logged": int(food["days_logged"] or 0),
        "water_glasses_total": int(water_count or 0),
        "workout_sessions": int(workout["sessions"] or 0),
        "calories_burned_total": int(workout["burned"] or 0),
        "active_minutes_total": int(workout["minutes"] or 0),
        "latest_weight_kg": float(weight["weight"]) if weight else None,
    }


# ---------------------------------------------------------------------------
# Chat endpoints
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(body: ChatRequest, user_id: CurrentUserDep, db: DbDep, redis: RedisDep):
    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)

    chat_repo = ChatRepository(db)
    history = await chat_repo.get_context(user_id, limit=20)
    user_info = await chat_repo.get_user_info_for_ai(user_id)

    user_repo = UserRepository(db)
    lang = await user_repo.get_lang(user_id) or "ru"

    today = await _today_snapshot(db, user_id)
    week = await _week_snapshot(db, user_id)

    meal_plan = None
    workout_plan = None
    cached_meal = await cache.get(f"meal_plan:{lang}:{user_id}") if cache else None
    cached_workout = await cache.get(f"workout_plan:{lang}:{user_id}") if cache else None
    if isinstance(cached_meal, dict):
        meal_plan = cached_meal.get("plan")
    if isinstance(cached_workout, dict):
        workout_plan = cached_workout.get("plan")

    # If the user explicitly attached a plan, fail loudly when it's missing
    # so the UI can prompt them to generate one first.
    if body.attach == "meal_plan" and not meal_plan:
        raise HTTPException(
            status_code=409,
            detail={"code": "no_meal_plan",
                    "message": "У тебя ещё нет активного плана питания. Сгенерируй его в разделе «Планы»."},
        )
    if body.attach == "workout_plan" and not workout_plan:
        raise HTTPException(
            status_code=409,
            detail={"code": "no_workout_plan",
                    "message": "У тебя ещё нет активного плана тренировок. Сгенерируй его в разделе «Планы»."},
        )

    try:
        response_text = await ai_service.chat(
            body.message,
            history,
            user_info,
            lang,
            today=today,
            week=week,
            meal_plan=meal_plan if body.attach != "workout_plan" else None,
            workout_plan=workout_plan if body.attach != "meal_plan" else None,
        )
    except Exception as e:
        logger.warning("AI chat failed: %s", e)
        raise _ai_http_error(e)

    inserted_id: int | None = None
    try:
        async with db.acquire() as conn, conn.transaction():
            await conn.execute(
                "INSERT INTO chat_history (user_id, message_type, message_text) "
                "VALUES ($1, 'user', $2)",
                user_id, body.message,
            )
            inserted_id = await conn.fetchval(
                "INSERT INTO chat_history (user_id, message_type, message_text) "
                "VALUES ($1, 'assistant', $2) RETURNING id",
                user_id, response_text,
            )
    except Exception as e:
        logger.error("AI chat: failed to persist conversation: %s", e)

    return ChatResponse(response=response_text, message_id=inserted_id)


@router.get("/chat/history", response_model=HistoryResponse)
async def chat_history(user_id: CurrentUserDep, db: DbDep, limit: int = 100):
    """Persisted chat history so the user sees their conversation across devices."""
    chat_repo = ChatRepository(db)
    rows = await chat_repo.get_history(user_id, limit=min(max(limit, 1), 500))
    return HistoryResponse(
        messages=[
            HistoryMessage(
                id=r["id"],
                role="user" if r["message_type"] == "user" else "assistant",
                text=r["message_text"] or "",
                created_at=r["created_at"].isoformat(),
            )
            for r in rows
        ]
    )


@router.delete("/chat/history")
async def clear_chat_history(user_id: CurrentUserDep, db: DbDep):
    chat_repo = ChatRepository(db)
    deleted = await chat_repo.clear_history(user_id)
    return {"deleted": deleted}


# ---------------------------------------------------------------------------
# Plan / recipe endpoints
# ---------------------------------------------------------------------------


def _plan_cache_key(kind: str, lang: str, user_id: int) -> str:
    return f"{kind}:{lang}:{user_id}"


@router.get("/plans")
async def get_active_plans(user_id: CurrentUserDep, db: DbDep, redis: RedisDep):
    """Return whatever plans are currently cached for this user."""
    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)
    lang = await UserRepository(db).get_lang(user_id) or "ru"
    meal = await cache.get(_plan_cache_key("meal_plan", lang, user_id))
    workout = await cache.get(_plan_cache_key("workout_plan", lang, user_id))
    return {
        "lang": lang,
        "meal_plan": meal.get("plan") if isinstance(meal, dict) else None,
        "workout_plan": workout.get("plan") if isinstance(workout, dict) else None,
    }


@router.post("/meal-plan")
async def generate_meal_plan(
    user_id: CurrentUserDep, db: DbDep, redis: RedisDep, refresh: bool = False,
):
    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)
    lang = await UserRepository(db).get_lang(user_id) or "ru"

    cache_key = _plan_cache_key("meal_plan", lang, user_id)
    if not refresh:
        cached = await cache.get(cache_key)
        if cached:
            return cached

    chat_repo = ChatRepository(db)
    user_info = await chat_repo.get_user_info_for_ai(user_id)
    try:
        plan = await ai_service.generate_meal_plan(user_info, lang)
    except Exception as e:
        logger.warning("AI meal plan failed: %s", e)
        raise _ai_http_error(e)
    result = {"plan": plan, "lang": lang}
    await cache.set(cache_key, result, settings.CACHE_TTL_RECIPES)
    return result


@router.post("/workout-plan")
async def generate_workout_plan(
    user_id: CurrentUserDep, db: DbDep, redis: RedisDep, refresh: bool = False,
):
    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)
    lang = await UserRepository(db).get_lang(user_id) or "ru"

    cache_key = _plan_cache_key("workout_plan", lang, user_id)
    if not refresh:
        cached = await cache.get(cache_key)
        if cached:
            return cached

    chat_repo = ChatRepository(db)
    user_info = await chat_repo.get_user_info_for_ai(user_id)
    try:
        plan = await ai_service.generate_workout_plan(user_info, lang)
    except Exception as e:
        logger.warning("AI workout plan failed: %s", e)
        raise _ai_http_error(e)
    result = {"plan": plan, "lang": lang}
    await cache.set(cache_key, result, settings.CACHE_TTL_RECIPES)
    return result


@router.post("/recipe")
async def generate_recipe(
    body: RecipeRequest, user_id: CurrentUserDep, db: DbDep, redis: RedisDep,
):
    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)
    lang = await UserRepository(db).get_lang(user_id) or "ru"

    cache_key = f"recipe:{lang}:{user_id}:{body.meal_type}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    chat_repo = ChatRepository(db)
    user_info = await chat_repo.get_user_info_for_ai(user_id)
    try:
        recipe = await ai_service.generate_recipe(body.meal_type, user_info, lang)
    except Exception as e:
        logger.warning("AI recipe failed: %s", e)
        raise _ai_http_error(e)
    result = {"recipe": recipe, "meal_type": body.meal_type, "lang": lang}
    await cache.set(cache_key, result, settings.CACHE_TTL_RECIPES)
    return result
