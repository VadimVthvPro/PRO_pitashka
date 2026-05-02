import logging
from datetime import date
from fastapi import APIRouter, HTTPException, Query
from app.dependencies import DbDep, CurrentUserDep, RedisDep
from app.models.workout import WorkoutSaveRequest, WorkoutSaveResponse, WorkoutType, CustomWorkoutRequest
from app.repositories.workout_repo import WorkoutRepository
from app.repositories.user_repo import UserRepository
from app.services import streak_service, ai_service, quota_service
from app.services.quota_service import QuotaExceeded

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/types", response_model=list[WorkoutType])
async def get_workout_types(db: DbDep, user_id: CurrentUserDep, lang: str = Query(default="ru")):
    repo = WorkoutRepository(db)
    types = await repo.get_training_types(lang)
    return [WorkoutType(**t) for t in types]


@router.post("")
async def save_workout(body: WorkoutSaveRequest, user_id: CurrentUserDep, db: DbDep):
    repo = WorkoutRepository(db)
    training = await repo.get_training_by_id(body.training_type_id)
    if not training:
        raise HTTPException(status_code=404, detail="Training type not found")

    calories = await repo.calculate_calories(body.training_type_id, body.duration_minutes, user_id)

    if calories == 0:
        user_repo = UserRepository(db)
        health = await user_repo.get_health(user_id)
        if health:
            base_coeff = training["base_coefficient"]
            calories = round(base_coeff * body.duration_minutes * (health["weight"] / 70), 1)

    await repo.save(
        user_id=user_id,
        training_type_id=body.training_type_id,
        training_name=training["name_ru"],
        workout_date=body.workout_date,
        duration=body.duration_minutes,
        calories=calories,
    )

    total_cal = await repo.get_total_calories(user_id, body.workout_date)
    total_dur = await repo.get_total_duration(user_id, body.workout_date)

    streak = None
    new_badges: list = []
    if body.workout_date == date.today():
        update = await streak_service.safe_touch_activity(db, user_id)
        streak = {
            "current": update.current,
            "longest": update.longest,
            "status": update.status,
            "freezes_available": update.freezes_available,
        }
        new_badges = update.newly_earned_badges

    return {
        "training_name": training["name_ru"],
        "duration": body.duration_minutes,
        "calories": calories,
        "total_today_cal": total_cal,
        "total_today_duration": total_dur,
        "streak": streak,
        "newly_earned_badges": new_badges,
    }


@router.post("/custom")
async def custom_workout(
    body: CustomWorkoutRequest, user_id: CurrentUserDep, db: DbDep, redis: RedisDep,
    lang: str = Query(default="ru"),
):
    try:
        await quota_service.check_and_increment(redis, user_id, "ai_workout")
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc))

    user_repo = UserRepository(db)
    health = await user_repo.get_health(user_id)
    user_info = dict(health) if health else {"weight": 70}

    try:
        result = await ai_service.analyze_custom_workout(body.description, user_info, lang)
    except ai_service.AIQuotaError:
        raise HTTPException(status_code=429, detail="AI quota exceeded")
    except (ai_service.AIConfigError, ai_service.AIUpstreamError) as exc:
        logger.error("AI custom workout error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service unavailable")

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    name = str(result.get("name", "Custom workout"))
    calories = float(result.get("calories", 0))
    duration = int(result.get("duration_minutes", 30))

    repo = WorkoutRepository(db)
    await repo.save(
        user_id=user_id,
        training_type_id=None,
        training_name=name,
        workout_date=body.workout_date,
        duration=duration,
        calories=calories,
    )

    total_cal = await repo.get_total_calories(user_id, body.workout_date)
    total_dur = await repo.get_total_duration(user_id, body.workout_date)

    streak = None
    new_badges: list = []
    if body.workout_date == date.today():
        update = await streak_service.safe_touch_activity(db, user_id)
        streak = {
            "current": update.current,
            "longest": update.longest,
            "status": update.status,
            "freezes_available": update.freezes_available,
        }
        new_badges = update.newly_earned_badges

    return {
        "training_name": name,
        "duration": duration,
        "calories": calories,
        "total_today_cal": total_cal,
        "total_today_duration": total_dur,
        "streak": streak,
        "newly_earned_badges": new_badges,
    }


@router.get("")
async def get_workouts(
    user_id: CurrentUserDep, db: DbDep,
    workout_date: date = Query(alias="date", default_factory=date.today),
):
    repo = WorkoutRepository(db)
    items = await repo.get_by_date(user_id, workout_date)
    total_cal = await repo.get_total_calories(user_id, workout_date)
    return {"date": workout_date.isoformat(), "items": items, "total_calories": total_cal}
