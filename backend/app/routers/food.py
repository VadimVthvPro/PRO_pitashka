import logging
from datetime import date
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from app.dependencies import DbDep, CurrentUserDep, RedisDep
from app.models.food import FoodManualRequest, FoodUpdateRequest
from app.repositories.food_repo import FoodRepository
from app.services import ai_service, streak_service, quota_service
from app.services.quota_service import QuotaExceeded
from app.services.cache_service import CacheService
from app.services.media_service import save_user_photo
from app.repositories.user_repo import UserRepository
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _photo_quota_error(exc: QuotaExceeded) -> HTTPException:
    st = exc.status
    return HTTPException(
        status_code=402,
        detail={
            "code": "quota_exceeded", "message": exc.message,
            "plan_key": st.plan_key, "tier": st.tier, "quota_key": st.key,
            "limit": st.limit, "used": st.used,
            "reset_at": st.reset_at.isoformat() if st.reset_at else None,
            "upgrade": {"suggested_plan_key": "premium_month" if st.tier == "free" else "pro_month",
                        "billing_url": "/billing"},
        },
    )


@router.post("")
async def add_food_manual(body: FoodManualRequest, user_id: CurrentUserDep, db: DbDep, redis: RedisDep):
    if len(body.foods) != len(body.grams):
        raise HTTPException(status_code=422, detail="Foods and grams must have same length")

    try:
        await quota_service.consume(db, redis, user_id, "food_manual", n=max(1, len(body.foods)))
    except QuotaExceeded as exc:
        raise _photo_quota_error(exc)

    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)
    lang = await UserRepository(db).get_lang(user_id) or "ru"

    cache_key = f"food:{lang}:{':'.join(body.foods)}:{':'.join(str(g) for g in body.grams)}"
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
                ai_items = await ai_service.analyze_food_text(ai_needed_foods, ai_needed_grams, lang=lang)
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
        update = await streak_service.safe_touch_activity(db, user_id)
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
    user_id: CurrentUserDep, db: DbDep, redis: RedisDep,
    file: UploadFile = File(...),
    food_date: date = Query(default_factory=date.today),
):
    """Принять фото тарелки → распознать в Gemini → сохранить позиции в БД.

    Сохраняем одну нормализованную копию (jpeg, длинная сторона 1600px, без
    EXIF) в `/uploads/food/{user_id}/`, URL пишем в каждую распознанную
    позицию — так в ленте дня и в ответе AI-чата видно «с какой тарелки».

    Квоту (`ai_photo`) тратим ДО сохранения файла, но ПОСЛЕ валидации — чтобы
    битый jpeg не съедал попытку. Фото сохраняем ДО вызова AI: если Gemini
    упал, файл всё равно привязываем к ручным попыткам повторить через /chat.
    """
    # 1. Считаем байты и валидируем размер/формат (раньше квоты — иначе 6 МБ
    #    .HEIC могли бы сжигать попытку впустую).
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Пустой файл")

    try:
        await quota_service.consume(db, redis, user_id, "ai_photo")
    except QuotaExceeded as exc:
        raise _photo_quota_error(exc)

    # 2. Сохраняем нормализованную копию. Если изображение битое — 4xx до AI.
    try:
        photo_url, jpeg_bytes, _ = save_user_photo(
            kind="food",
            user_id=user_id,
            raw=image_bytes,
            content_type=file.content_type,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("food.photo: save failed user=%s: %s", user_id, exc)
        # Fallback на сырые байты — AI ещё может распознать, но URL не привяжем
        photo_url = None
        jpeg_bytes = image_bytes

    # 3. AI — на нормализованной копии (меньше трафика в Gemini).
    lang = await UserRepository(db).get_lang(user_id) or "ru"
    try:
        items = await ai_service.recognize_food_photo(jpeg_bytes, lang=lang)
    except Exception as e:
        logger.warning("AI photo recognition failed: %s", e)
        # Файл оставляем — пригодится для ручного ввода/повтора.
        raise HTTPException(
            status_code=503,
            detail="AI-сервис временно недоступен. Попробуйте позже или добавьте еду вручную.",
        )

    # 4. Пишем строки в БД, прикрепляя URL снимка к каждому блюду с одной тарелки.
    repo = FoodRepository(db)
    enriched_items: list[dict] = []
    for item in items:
        row = await repo.add(
            user_id=user_id, food_date=food_date,
            name=item.get("name", ""),
            protein=item.get("b", 0), fat=item.get("g", 0),
            carbs=item.get("u", 0), calories=item.get("cal", 0),
            photo_url=photo_url,
        )
        enriched = dict(item)
        enriched["photo_url"] = photo_url
        enriched["id"] = row.get("id")
        enriched_items.append(enriched)

    streak = None
    new_badges: list = []
    if enriched_items and food_date == date.today():
        update = await streak_service.safe_touch_activity(db, user_id)
        streak = {
            "current": update.current,
            "longest": update.longest,
            "status": update.status,
            "freezes_available": update.freezes_available,
        }
        new_badges = update.newly_earned_badges

    return {
        "items": enriched_items,
        "photo_url": photo_url,
        "streak": streak,
        "newly_earned_badges": new_badges,
    }


@router.get("")
async def get_food(
    user_id: CurrentUserDep, db: DbDep,
    food_date: date = Query(alias="date", default_factory=date.today),
):
    repo = FoodRepository(db)
    items = await repo.get_by_date(user_id, food_date)
    totals = await repo.get_daily_totals(user_id, food_date)
    return {"date": food_date.isoformat(), "items": items, "totals": totals}


@router.get("/search")
async def search_foods_endpoint(
    user_id: CurrentUserDep,
    q: str = Query(..., min_length=1, max_length=64),
    limit: int = Query(default=10, ge=1, le=30),
):
    from app.utils.food_fallback import search_foods
    return {"items": search_foods(q, limit)}


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
        streak_update = await streak_service.safe_touch_activity(db, user_id)
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


@router.patch("/{food_id}")
async def update_food_item(
    food_id: int, body: FoodUpdateRequest, user_id: CurrentUserDep, db: DbDep,
):
    repo = FoodRepository(db)
    updated = await repo.update_by_id(
        user_id=user_id, food_id=food_id,
        name=body.name, protein=body.b, fat=body.g, carbs=body.u, calories=body.cal,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return updated


@router.delete("/{food_id}")
async def delete_food_item(food_id: int, user_id: CurrentUserDep, db: DbDep):
    repo = FoodRepository(db)
    deleted = await repo.delete_by_id(user_id, food_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return {"ok": True}
