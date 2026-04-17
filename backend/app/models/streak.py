from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel


StreakStatus = Literal["on_fire", "at_risk", "broken", "none"]


class StreakResponse(BaseModel):
    current: int
    longest: int
    status: StreakStatus
    freezes_available: int
    last_active_date: Optional[date] = None


class BadgeInfo(BaseModel):
    id: int
    code: str
    title: str
    description: str
    icon: str
    tier: str
    category: str


class EarnedBadge(BadgeInfo):
    earned_at: datetime


class BadgesOverview(BaseModel):
    earned: list[EarnedBadge]
    locked: list[BadgeInfo]
    total: int
