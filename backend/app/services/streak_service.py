"""
Streaks and achievement badges.

touch_activity(user_id) is called from every endpoint that represents
a meaningful daily action (adding food, water, workout, weight).

- Recomputes current/longest streak based on last_active_date.
- One automatic freeze per week covers a single missed day.
- Evaluates all badge conditions and grants newly-earned ones atomically.
- Returns a small DTO the client can use for toasts.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import asyncpg

from app.repositories.streak_repo import StreakRepository

logger = logging.getLogger(__name__)

WATER_DAILY_TARGET = 8
MACRO_BALANCE_TOLERANCE = 0.10


@dataclass
class StreakUpdate:
    current: int
    longest: int
    status: str
    freezes_available: int
    last_active_date: Optional[date]
    newly_earned_badges: list[dict]


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _compute_status(current: int, last_active: Optional[date], today: date) -> str:
    if current <= 0 or last_active is None:
        return "none"
    delta = (today - last_active).days
    if delta == 0:
        return "on_fire"
    if delta == 1:
        return "at_risk"
    return "broken"


async def get_streak_dto(pool: asyncpg.Pool, user_id: int) -> dict:
    repo = StreakRepository(pool)
    row = await repo.get_streak(user_id)
    today = date.today()
    if not row:
        return {
            "current": 0,
            "longest": 0,
            "status": "none",
            "freezes_available": 1,
            "last_active_date": None,
        }

    current = int(row["current_streak"])
    last_active: Optional[date] = row["last_active_date"]

    # If they already missed more than one day AND have no freeze — show 0.
    if last_active is not None:
        delta = (today - last_active).days
        if delta >= 2:
            current = 0

    status = _compute_status(current, last_active, today)
    return {
        "current": current,
        "longest": int(row["longest_streak"]),
        "status": status,
        "freezes_available": int(row["freezes_available"]),
        "last_active_date": last_active,
    }


async def touch_activity(pool: asyncpg.Pool, user_id: int) -> StreakUpdate:
    """
    Update the streak for today and evaluate badges.
    Idempotent — calling it 10 times today still leaves the streak unchanged
    on subsequent calls.
    """
    repo = StreakRepository(pool)
    today = date.today()
    row = await repo.get_streak(user_id)

    if row is None:
        current = 1
        longest = 1
        freezes = 1
        last_freeze_reset = _monday(today)
    else:
        current = int(row["current_streak"])
        longest = int(row["longest_streak"])
        freezes = int(row["freezes_available"])
        last_active: Optional[date] = row["last_active_date"]
        last_freeze_reset: Optional[date] = row["last_freeze_reset"]

        # Weekly freeze refill (every Monday)
        this_week_monday = _monday(today)
        if last_freeze_reset is None or last_freeze_reset < this_week_monday:
            freezes = 1
            last_freeze_reset = this_week_monday

        if last_active is None:
            current = 1
        else:
            delta = (today - last_active).days
            if delta == 0:
                pass
            elif delta == 1:
                current += 1
            elif delta == 2 and freezes >= 1:
                freezes -= 1
                current += 1
                logger.info("User %s: freeze auto-applied, streak kept at %d", user_id, current)
            else:
                current = 1

        longest = max(longest, current)

    await repo.upsert_streak(
        user_id=user_id,
        current=current,
        longest=longest,
        last_active=today,
        freezes=freezes,
        last_freeze_reset=last_freeze_reset,
    )

    newly_earned = await _evaluate_badges(repo, user_id, current)

    status = _compute_status(current, today, today)
    return StreakUpdate(
        current=current,
        longest=longest,
        status=status,
        freezes_available=freezes,
        last_active_date=today,
        newly_earned_badges=newly_earned,
    )


async def _evaluate_badges(
    repo: StreakRepository, user_id: int, current_streak: int
) -> list[dict]:
    """Check every badge condition, grant new ones, return the newly-earned list."""
    earned = await repo.earned_codes(user_id)
    newly: list[dict] = []

    async def try_grant(code: str) -> None:
        if code in earned:
            return
        granted = await repo.grant_badge(user_id, code)
        if granted:
            newly.append({
                "id": granted["id"],
                "code": granted["code"],
                "title": granted["title"],
                "description": granted["description"],
                "icon": granted["icon"],
                "tier": granted["tier"],
                "category": granted["category"],
                "earned_at": granted["earned_at"].isoformat() if granted.get("earned_at") else None,
            })

    # --- streak tiers ---
    if current_streak >= 3:
        await try_grant("streak_3")
    if current_streak >= 7:
        await try_grant("streak_7")
    if current_streak >= 30:
        await try_grant("streak_30")
    if current_streak >= 100:
        await try_grant("streak_100")

    # --- water ---
    if await repo.water_count_total(user_id) >= 1:
        await try_grant("water_first")
    if await repo.water_today(user_id) >= WATER_DAILY_TARGET:
        await try_grant("water_goal")
    if await repo.water_goal_streak(user_id, WATER_DAILY_TARGET) >= 7:
        await try_grant("water_7")

    # --- food ---
    if await repo.food_entries_count(user_id) >= 1:
        await try_grant("food_first")

    totals = await repo.food_totals_today(user_id)
    daily_cal = await repo.user_daily_cal(user_id)
    if totals and daily_cal and totals["calories"] and totals["calories"] > 0:
        target_protein = (daily_cal * 0.30) / 4
        target_fat = (daily_cal * 0.25) / 9
        target_carbs = (daily_cal * 0.45) / 4

        def in_band(value: float, target: float) -> bool:
            if target <= 0:
                return False
            return abs(value - target) / target <= MACRO_BALANCE_TOLERANCE

        if (
            in_band(float(totals["protein"]), target_protein)
            and in_band(float(totals["fat"]), target_fat)
            and in_band(float(totals["carbs"]), target_carbs)
        ):
            await try_grant("food_balance")

    # --- workouts ---
    if await repo.workouts_count(user_id) >= 1:
        await try_grant("workout_first")

    if await repo.workouts_in_week(user_id, _monday(date.today())) >= 5:
        await try_grant("workout_5wk")

    return newly
