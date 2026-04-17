from datetime import date
from fastapi import APIRouter, HTTPException, Query
from app.dependencies import DbDep, CurrentUserDep
from app.models.workout import WorkoutSaveRequest, WorkoutSaveResponse, WorkoutType
from app.repositories.workout_repo import WorkoutRepository
from app.repositories.user_repo import UserRepository
from app.services import streak_service

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
        update = await streak_service.touch_activity(db, user_id)
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


@router.get("")
async def get_workouts(
    user_id: CurrentUserDep, db: DbDep,
    workout_date: date = Query(alias="date", default_factory=date.today),
):
    repo = WorkoutRepository(db)
    items = await repo.get_by_date(user_id, workout_date)
    total_cal = await repo.get_total_calories(user_id, workout_date)
    return {"date": workout_date.isoformat(), "items": items, "total_calories": total_cal}
