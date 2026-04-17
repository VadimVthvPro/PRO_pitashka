from datetime import date
from fastapi import APIRouter, Query
from app.dependencies import DbDep, CurrentUserDep
from app.models.water import WaterResponse
from app.repositories.water_repo import WaterRepository

router = APIRouter()

GLASS_ML = 300


@router.post("", response_model=WaterResponse)
async def add_water(user_id: CurrentUserDep, db: DbDep):
    repo = WaterRepository(db)
    count = await repo.add_glass(user_id)
    return WaterResponse(count=count, ml=count * GLASS_ML)


@router.get("", response_model=WaterResponse)
async def get_water(
    user_id: CurrentUserDep, db: DbDep,
    water_date: date = Query(alias="date", default_factory=date.today),
):
    repo = WaterRepository(db)
    count = await repo.get_by_date(user_id, water_date)
    return WaterResponse(count=count, ml=count * GLASS_ML)
