from datetime import date
from fastapi import APIRouter, Query
from app.dependencies import DbDep, CurrentUserDep
from app.repositories.summary_repo import SummaryRepository

router = APIRouter()


@router.get("/day")
async def get_day_summary(
    user_id: CurrentUserDep, db: DbDep,
    day: date = Query(alias="date", default_factory=date.today),
):
    repo = SummaryRepository(db)
    return await repo.get_day(user_id, day)


@router.get("/month")
async def get_month_summary(
    user_id: CurrentUserDep, db: DbDep,
    year: int = Query(...), month: int = Query(ge=1, le=12),
):
    repo = SummaryRepository(db)
    return await repo.get_month(user_id, year, month)


@router.get("/year")
async def get_year_summary(
    user_id: CurrentUserDep, db: DbDep,
    year: int = Query(...),
):
    repo = SummaryRepository(db)
    return await repo.get_year(user_id, year)
