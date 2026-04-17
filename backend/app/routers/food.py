import logging
from datetime import date
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from app.dependencies import DbDep, CurrentUserDep, RedisDep
from app.models.food import FoodManualRequest
from app.repositories.food_repo import FoodRepository
from app.services import ai_service, streak_service
from app.services.cache_service import CacheService
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("")
async def add_food_manual(body: FoodManualRequest, user_id: CurrentUserDep, db: DbDep, redis: RedisDep):
    if len(body.foods) != len(body.grams):
        raise HTTPException(status_code=422, detail="Foods and grams must have same length")

    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)

    cache_key = f"food:{':'.join(body.foods)}:{':'.join(str(g) for g in body.grams)}"
    cached = await cache.get(cache_key)

    if cached:
        items = cached
    else:
        from app.utils.food_fallback import find_food, calculate_nutrition
        items = []
        fallback_used = []
        ai_needed_foods = []
        ai_needed_grams = []

        for food_name, grams in zip(body.foods, body.grams):
            fb = find_food(food_name)
            if fb:
                nutrition = calculate_nutrition(fb, grams)
                items.append({"name": food_name, "grams": grams, **nutrition})
                fallback_used.append(True)
            else:
                ai_needed_foods.append(food_name)
                ai_needed_grams.append(grams)
                fallback_used.append(False)

        if ai_needed_foods:
            try:
                ai_items = await ai_service.analyze_food_text(ai_needed_foods, ai_needed_grams)
                items.extend(ai_items)
            except Exception as e:
                logger.warning("AI food analysis failed: %s", e)
                for food_name, grams in zip(ai_needed_foods, ai_needed_grams):
                    items.append({"name": food_name, "grams": grams, "cal": 0, "b": 0, "g": 0, "u": 0, "ai_error": True})

        await cache.set(cache_key, items, settings.CACHE_TTL_FOOD_RECOGNITION)

    repo = FoodRepository(db)
    saved = []
    for item in items:
        row = await repo.add(
            user_id=user_id, food_date=body.food_date,
            name=item.get("name", ""),
            protein=item.get("b", 0), fat=item.get("g", 0),
            carbs=item.get("u", 0), calories=item.get("cal", 0),
        )
        saved.append(row)

    streak = None
    new_badges: list = []
    if saved and body.food_date == date.today():
        update = await streak_service.touch_activity(db, user_id)
        streak = {
            "current": update.current,
            "longest": update.longest,
            "status": update.status,
            "freezes_available": update.freezes_available,
        }
        new_badges = update.newly_earned_badges

    return {"items": items, "saved": len(saved), "streak": streak, "newly_earned_badges": new_badges}


@router.post("/photo")
async def add_food_photo(
    user_id: CurrentUserDep, db: DbDep,
    file: UploadFile = File(...),
    food_date: date = Query(default_factory=date.today),
):
    image_bytes = await file.read()
    try:
        items = await ai_service.recognize_food_photo(image_bytes)
    except Exception as e:
        logger.warning("AI photo recognition failed: %s", e)
        raise HTTPException(status_code=503, detail="AI-сервис временно недоступен. Попробуйте позже или добавьте еду вручную.")

    repo = FoodRepository(db)
    for item in items:
        await repo.add(
            user_id=user_id, food_date=food_date,
            name=item.get("name", ""),
            protein=item.get("b", 0), fat=item.get("g", 0),
            carbs=item.get("u", 0), calories=item.get("cal", 0),
        )

    streak = None
    new_badges: list = []
    if items and food_date == date.today():
        update = await streak_service.touch_activity(db, user_id)
        streak = {
            "current": update.current,
            "longest": update.longest,
            "status": update.status,
            "freezes_available": update.freezes_available,
        }
        new_badges = update.newly_earned_badges

    return {"items": items, "streak": streak, "newly_earned_badges": new_badges}


@router.get("")
async def get_food(
    user_id: CurrentUserDep, db: DbDep,
    food_date: date = Query(alias="date", default_factory=date.today),
):
    repo = FoodRepository(db)
    items = await repo.get_by_date(user_id, food_date)
    totals = await repo.get_daily_totals(user_id, food_date)
    return {"date": food_date.isoformat(), "items": items, "totals": totals}


@router.get("/favorites")
async def get_favorites(user_id: CurrentUserDep, db: DbDep, limit: int = 12):
    repo = FoodRepository(db)
    items = await repo.get_favorites(user_id, limit=min(max(limit, 1), 50))
    return {"items": items}


@router.get("/last-day")
async def last_day_with_food(user_id: CurrentUserDep, db: DbDep):
    """Returns the most recent past date that has food entries + its items."""
    repo = FoodRepository(db)
    last = await repo.get_last_day_with_food(user_id, date.today())
    if not last:
        return {"date": None, "items": [], "totals": None}
    items = await repo.get_by_date(user_id, last)
    totals = await repo.get_daily_totals(user_id, last)
    return {"date": last.isoformat(), "items": items, "totals": totals}


@router.post("/repeat")
async def repeat_day(
    user_id: CurrentUserDep, db: DbDep,
    source: str = Query(default="yesterday"),  # "yesterday" | "last_meal"
    target_date: date = Query(default_factory=date.today),
):
    repo = FoodRepository(db)
    if source == "yesterday":
        from datetime import timedelta
        src = target_date - timedelta(days=1)
        existing = await repo.get_by_date(user_id, src)
        if not existing:
            raise HTTPException(status_code=404, detail="Вчера в дневнике пусто — повторять нечего")
    elif source == "last_meal":
        src = await repo.get_last_day_with_food(user_id, target_date)
        if not src:
            raise HTTPException(status_code=404, detail="В дневнике ещё нет записей")
    else:
        raise HTTPException(status_code=422, detail="Unknown source")

    copied = await repo.copy_day(user_id, src, target_date)
    if copied == 0:
        raise HTTPException(status_code=404, detail="Нечего копировать")

    update = None
    new_badges: list = []
    if target_date == date.today():
        streak_update = await streak_service.touch_activity(db, user_id)
        update = {
            "current": streak_update.current,
            "longest": streak_update.longest,
            "status": streak_update.status,
            "freezes_available": streak_update.freezes_available,
        }
        new_badges = streak_update.newly_earned_badges

    return {
        "copied": copied,
        "source_date": src.isoformat(),
        "target_date": target_date.isoformat(),
        "streak": update,
        "newly_earned_badges": new_badges,
    }
