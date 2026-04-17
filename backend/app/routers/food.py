from datetime import date
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from app.dependencies import DbDep, CurrentUserDep, RedisDep
from app.models.food import FoodManualRequest
from app.repositories.food_repo import FoodRepository
from app.services import ai_service
from app.services.cache_service import CacheService
from app.config import get_settings

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
            ai_items = await ai_service.analyze_food_text(ai_needed_foods, ai_needed_grams)
            items.extend(ai_items)

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
    return {"items": items, "saved": len(saved)}


@router.post("/photo")
async def add_food_photo(
    user_id: CurrentUserDep, db: DbDep,
    file: UploadFile = File(...),
    food_date: date = Query(default_factory=date.today),
):
    image_bytes = await file.read()
    items = await ai_service.recognize_food_photo(image_bytes)

    repo = FoodRepository(db)
    for item in items:
        await repo.add(
            user_id=user_id, food_date=food_date,
            name=item.get("name", ""),
            protein=item.get("b", 0), fat=item.get("g", 0),
            carbs=item.get("u", 0), calories=item.get("cal", 0),
        )
    return {"items": items}


@router.get("")
async def get_food(
    user_id: CurrentUserDep, db: DbDep,
    food_date: date = Query(alias="date", default_factory=date.today),
):
    repo = FoodRepository(db)
    items = await repo.get_by_date(user_id, food_date)
    totals = await repo.get_daily_totals(user_id, food_date)
    return {"date": food_date.isoformat(), "items": items, "totals": totals}
