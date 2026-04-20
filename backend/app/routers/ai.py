import logging
import time
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.dependencies import CurrentUserDep, DbDep, RedisDep
from app.models.ai import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    HistoryMessage,
    HistoryResponse,
    QuickPrompt,
    QuickPromptsResponse,
    RecipeRequest,
    RegenerateResponse,
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


async def _resolve_chat_context(
    db, redis, user_id: int, attach: str | None
) -> tuple[list[dict], dict, str, dict, dict, str | None, str | None]:
    """Gather everything the chat() service needs.

    Pulled into a helper because both ``/chat`` and ``/chat/regenerate`` need
    the *exact same* context window — easy to drift apart otherwise."""
    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)

    chat_repo = ChatRepository(db)
    history = await chat_repo.get_context(user_id, limit=20)
    user_info = await chat_repo.get_user_info_for_ai(user_id)
    lang = await UserRepository(db).get_lang(user_id) or "ru"

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

    if attach == "meal_plan" and not meal_plan:
        raise HTTPException(
            status_code=409,
            detail={"code": "no_meal_plan",
                    "message": "У тебя ещё нет активного плана питания. Сгенерируй его в разделе «Планы»."},
        )
    if attach == "workout_plan" and not workout_plan:
        raise HTTPException(
            status_code=409,
            detail={"code": "no_workout_plan",
                    "message": "У тебя ещё нет активного плана тренировок. Сгенерируй его в разделе «Планы»."},
        )

    return history, user_info, lang, today, week, meal_plan, workout_plan


async def _enforce_ai_access(db, user_id: int) -> None:
    """Deny AI access for banned, AI-disabled or globally-off configurations.

    Runs before every chat turn. Matches the language of the user-visible
    error text to whatever's in `user_lang` for this user — but since we
    don't want an extra query here, we stick to RU for the rare deny paths.
    """
    from app.services.runtime_settings import get_setting as _get_setting
    if not bool(await _get_setting("ai_chat_enabled")):
        raise HTTPException(
            status_code=503,
            detail={"code": "ai_disabled_globally",
                    "message": "AI-чат временно отключён администрацией."},
        )
    row = await db.fetchrow(
        "SELECT banned_at, ai_disabled FROM user_main WHERE user_id = $1",
        user_id,
    )
    if row and row["banned_at"] is not None:
        raise HTTPException(
            status_code=403,
            detail={"code": "user_banned",
                    "message": "Аккаунт заблокирован администрацией."},
        )
    if row and row["ai_disabled"]:
        raise HTTPException(
            status_code=403,
            detail={"code": "ai_disabled_for_user",
                    "message": "AI-чат недоступен для этого аккаунта."},
        )


async def _run_chat_and_persist(
    db,
    redis,
    user_id: int,
    *,
    user_message: str,
    attach: str | None,
    persist_user: bool,
) -> tuple[str, int | None, int, str | None]:
    """Run a chat turn end-to-end. Returns (text, assistant_msg_id, latency_ms, model).

    ``persist_user=False`` is used by /regenerate, which keeps the original
    user message and only swaps in a fresh assistant reply.
    """
    await _enforce_ai_access(db, user_id)
    history, user_info, lang, today, week, meal_plan, workout_plan = (
        await _resolve_chat_context(db, redis, user_id, attach)
    )

    started = time.perf_counter()
    try:
        response_text = await ai_service.chat(
            user_message,
            history,
            user_info,
            lang,
            today=today,
            week=week,
            meal_plan=meal_plan if attach != "workout_plan" else None,
            workout_plan=workout_plan if attach != "meal_plan" else None,
        )
    except Exception as e:
        logger.warning("AI chat failed: %s", e)
        raise _ai_http_error(e)
    latency_ms = int((time.perf_counter() - started) * 1000)
    # Record the *effective* model (runtime override wins over env) so the
    # admin log shows exactly which model produced each reply.
    model_name = ai_service._current_model_name()  # noqa: SLF001

    chat_repo = ChatRepository(db)
    inserted_id: int | None = None
    try:
        if persist_user:
            await chat_repo.save_user_message(user_id, user_message)
        inserted_id = await chat_repo.save_assistant_message(
            user_id,
            response_text,
            attach_kind=attach,
            latency_ms=latency_ms,
            model=model_name,
        )
    except Exception as e:
        logger.error("AI chat: failed to persist conversation: %s", e)

    return response_text, inserted_id, latency_ms, model_name


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(body: ChatRequest, user_id: CurrentUserDep, db: DbDep, redis: RedisDep):
    text, msg_id, latency_ms, model_name = await _run_chat_and_persist(
        db,
        redis,
        user_id,
        user_message=body.message,
        attach=body.attach,
        persist_user=True,
    )
    return ChatResponse(
        response=text,
        message_id=msg_id,
        latency_ms=latency_ms,
        model=model_name,
    )


@router.post("/chat/regenerate", response_model=RegenerateResponse)
async def ai_chat_regenerate(user_id: CurrentUserDep, db: DbDep, redis: RedisDep):
    """Drop the last assistant reply and re-run the model on the same prompt.

    The user message stays exactly where it was — only the assistant's turn
    is replaced. Useful when a reply was off-topic or the user wants a
    different angle without re-typing.
    """
    chat_repo = ChatRepository(db)
    deleted_id, prev_text = await chat_repo.delete_last_assistant(user_id)
    if not prev_text:
        raise HTTPException(
            status_code=409,
            detail={"code": "no_message_to_regen",
                    "message": "Нечего перегенерировать — отправь сначала сообщение."},
        )
    text, msg_id, latency_ms, model_name = await _run_chat_and_persist(
        db,
        redis,
        user_id,
        user_message=prev_text,
        attach=None,
        persist_user=False,
    )
    if msg_id is None:
        # Persistence failed AND we already nuked the previous reply — surface
        # an error rather than silently losing both turns.
        raise HTTPException(
            status_code=500,
            detail={"code": "regen_persist_failed",
                    "message": "Ответ сгенерирован, но не сохранился. Попробуй ещё раз."},
        )
    return RegenerateResponse(
        response=text,
        message_id=msg_id,
        deleted_id=deleted_id,
        latency_ms=latency_ms,
        model=model_name,
    )


@router.post("/chat/feedback")
async def ai_chat_feedback(body: FeedbackRequest, user_id: CurrentUserDep, db: DbDep):
    """Record 👍 / 👎 (or clear it) on an assistant message owned by the user."""
    ok = await ChatRepository(db).set_feedback(user_id, body.message_id, body.value)
    if not ok:
        raise HTTPException(status_code=404, detail="message not found")
    return {"ok": True, "value": body.value}


# ---------------------------------------------------------------------------
# Quick prompts: cheap, deterministic suggestions tailored to today's snapshot.
# Renders chips above the composer so the user always has something to ask.
# Intentionally NOT a Gemini call — it would defeat the point of "instant".
# ---------------------------------------------------------------------------


def _quick_prompts(today: dict, week: dict, lang: str, has_meal: bool, has_workout: bool) -> list[QuickPrompt]:
    L = lang.lower()
    is_ru = L.startswith("ru")

    def s(ru: str, en: str) -> str:
        return ru if is_ru else en

    cal = today.get("calories_in", 0) or 0
    water = today.get("water_glasses", 0) or 0
    burned = today.get("calories_burned", 0) or 0
    workouts = today.get("workout_sessions", 0) or 0
    days_logged = week.get("days_with_food_logged", 0) or 0

    out: list[QuickPrompt] = []

    # Most-relevant first — the chip with `accent=True` gets a coloured pill
    if cal > 0:
        out.append(QuickPrompt(
            icon="solar:chart-2-bold-duotone",
            label=s("Анализ дня", "Today's check-in"),
            prompt=s(
                f"Проанализируй мой сегодняшний день. Я съел {cal} ккал, "
                f"выпил {water} стаканов воды, сжёг {burned} ккал на тренировках. "
                "Что добавить или убрать до конца дня?",
                f"Review my day so far: {cal} kcal eaten, {water} glasses of water, "
                f"{burned} kcal burned. What should I add or skip until bedtime?",
            ),
            accent=True,
        ))
    else:
        out.append(QuickPrompt(
            icon="solar:plate-bold-duotone",
            label=s("Идея на завтрак", "Breakfast idea"),
            prompt=s(
                "Предложи лёгкий завтрак на 350-450 ккал из обычных продуктов.",
                "Suggest a light breakfast around 350-450 kcal from common ingredients.",
            ),
            accent=True,
        ))

    if workouts == 0:
        out.append(QuickPrompt(
            icon="solar:dumbbell-large-bold-duotone",
            label=s("15-минутная тренировка", "15-min workout"),
            prompt=s(
                "Дай мне короткую 15-минутную тренировку дома без инвентаря, "
                "с учётом моих параметров и цели.",
                "Give me a quick 15-minute home workout, no equipment, fitting my goals.",
            ),
        ))

    if water < 6:
        out.append(QuickPrompt(
            icon="solar:cup-bold-duotone",
            label=s("Почему мало воды?", "Hydration tip"),
            prompt=s(
                "Я выпил всего {n} стаканов воды. Сколько ещё стоит выпить и как себя приучить?".format(n=water),
                f"I had only {water} glasses of water. How much more do I need and how to build the habit?",
            ),
        ))

    if has_meal:
        out.append(QuickPrompt(
            icon="solar:notebook-bold-duotone",
            label=s("Замени блюдо в плане", "Swap a meal"),
            prompt=s(
                "В моём плане питания замени один приём пищи на что-то с похожими БЖУ — мне надоел текущий вариант.",
                "Swap one meal in my plan for something with similar macros — I'm bored with the current one.",
            ),
        ))
    else:
        out.append(QuickPrompt(
            icon="solar:document-add-bold-duotone",
            label=s("Сделай план питания", "Make a meal plan"),
            prompt=s(
                "Составь мне план питания на день под мою цель и привычки.",
                "Build me a one-day meal plan that fits my goal and habits.",
            ),
        ))

    if has_workout:
        out.append(QuickPrompt(
            icon="solar:dumbbell-bold-duotone",
            label=s("Скорректируй тренировку", "Adjust workout"),
            prompt=s(
                "В моём плане тренировок есть упражнения, которые мне неудобны. Подбери замены.",
                "Some moves in my workout plan don't suit me. Suggest replacements.",
            ),
        ))

    if days_logged >= 3:
        out.append(QuickPrompt(
            icon="solar:graph-up-bold-duotone",
            label=s("Что с прогрессом?", "How's progress?"),
            prompt=s(
                "Посмотри на мою неделю и скажи, в правильном ли я направлении двигаюсь.",
                "Look at my week and tell me whether I'm heading in the right direction.",
            ),
        ))

    return out[:5]


@router.get("/snapshot")
async def chat_snapshot(user_id: CurrentUserDep, db: DbDep, redis: RedisDep):
    """Lightweight context snapshot for the redesigned chat rail.

    Mirrors what the AI itself sees in the prompt so the user can verify
    the assistant is reasoning over the right numbers (today + this week,
    plan availability flags). Cheap to call repeatedly — pure SQL, no LLM.
    """
    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)
    lang = await UserRepository(db).get_lang(user_id) or "ru"
    today = await _today_snapshot(db, user_id)
    week = await _week_snapshot(db, user_id)
    cached_meal = await cache.get(f"meal_plan:{lang}:{user_id}") if cache else None
    cached_workout = await cache.get(f"workout_plan:{lang}:{user_id}") if cache else None
    return {
        "today": today,
        "week": week,
        "has_meal_plan": isinstance(cached_meal, dict) and bool(cached_meal.get("plan")),
        "has_workout_plan": isinstance(cached_workout, dict) and bool(cached_workout.get("plan")),
        "lang": lang,
    }


@router.get("/chat/quick-prompts", response_model=QuickPromptsResponse)
async def chat_quick_prompts(user_id: CurrentUserDep, db: DbDep, redis: RedisDep):
    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)
    lang = await UserRepository(db).get_lang(user_id) or "ru"
    today = await _today_snapshot(db, user_id)
    week = await _week_snapshot(db, user_id)
    cached_meal = await cache.get(f"meal_plan:{lang}:{user_id}") if cache else None
    cached_workout = await cache.get(f"workout_plan:{lang}:{user_id}") if cache else None
    has_meal = isinstance(cached_meal, dict) and bool(cached_meal.get("plan"))
    has_workout = isinstance(cached_workout, dict) and bool(cached_workout.get("plan"))
    return QuickPromptsResponse(
        prompts=_quick_prompts(today, week, lang, has_meal, has_workout),
    )


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
                feedback=r.get("feedback") if isinstance(r, dict) else r["feedback"],
                attach_kind=(r.get("attach_kind") if isinstance(r, dict) else r["attach_kind"]),
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
