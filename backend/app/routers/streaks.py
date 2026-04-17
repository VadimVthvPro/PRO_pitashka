from fastapi import APIRouter

from app.dependencies import DbDep, CurrentUserDep
from app.models.streak import StreakResponse, BadgesOverview, EarnedBadge, BadgeInfo
from app.repositories.streak_repo import StreakRepository
from app.services import streak_service

router = APIRouter()


@router.get("/me", response_model=StreakResponse)
async def my_streak(user_id: CurrentUserDep, db: DbDep) -> StreakResponse:
    dto = await streak_service.get_streak_dto(db, user_id)
    return StreakResponse(**dto)


@router.get("/badges", response_model=BadgesOverview)
async def my_badges(user_id: CurrentUserDep, db: DbDep) -> BadgesOverview:
    repo = StreakRepository(db)
    all_badges = await repo.list_badges()
    earned_rows = await repo.user_earned(user_id)
    earned_codes = {r["code"] for r in earned_rows}

    earned = [
        EarnedBadge(
            id=r["id"],
            code=r["code"],
            title=r["title"],
            description=r["description"],
            icon=r["icon"],
            tier=r["tier"],
            category=r["category"],
            earned_at=r["earned_at"],
        )
        for r in earned_rows
    ]
    locked = [
        BadgeInfo(
            id=b["id"],
            code=b["code"],
            title=b["title"],
            description=b["description"],
            icon=b["icon"],
            tier=b["tier"],
            category=b["category"],
        )
        for b in all_badges
        if b["code"] not in earned_codes
    ]

    return BadgesOverview(earned=earned, locked=locked, total=len(all_badges))
