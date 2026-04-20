"""Weight tracking, history and forecast.

The forecast combines two independent signals:

1. **Empirical trend** — ordinary least-squares fit over the user's recent
   weight history. Reliable once we have ≥ 7 data points across ≥ 14 days.
2. **Energy-balance trend** — predicted slope from the user's actual calorie
   intake (last 14 days) versus their estimated TDEE (Mifflin-St Jeor BMR
   times an activity coefficient). Each ~7700 kcal of surplus / deficit
   shifts body mass by ~1 kg.

We blend the two with a confidence weight that grows with history length:
short histories lean on the energy model, long ones lean on the data.
This makes the projection physically meaningful even with a few measurements,
and avoids the pathological "linear extrapolation forever" of a pure OLS line.

The endpoint accepts a `range` parameter so the chart can ask the backend
for the exact slice it needs (7d / 30d / 90d / 1y / all). This replaces the
old client-side filter, which meant 1y/all just showed a 90-day window.
"""

from datetime import date, timedelta
from statistics import mean
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Path, Query

from app.dependencies import DbDep, CurrentUserDep
from app.repositories.weight_repo import WeightRepository

router = APIRouter()


RANGE_DAYS: dict[str, Optional[int]] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "1y": 365,
    "all": None,
}

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}
DEFAULT_ACTIVITY = 1.4
KCAL_PER_KG_BODYMASS = 7700.0


@router.get("/history")
async def history(user_id: CurrentUserDep, db: DbDep, days: int = Query(default=90, ge=7, le=3650)):
    repo = WeightRepository(db)
    items = await repo.history(user_id, days)
    return {"items": items, "days": days}


@router.get("/list")
async def list_entries(user_id: CurrentUserDep, db: DbDep, limit: int = Query(default=180, ge=1, le=3650)):
    """Newest-first list for the editable journal."""
    repo = WeightRepository(db)
    return {"items": await repo.list_entries(user_id, limit=limit)}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        d = date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=422, detail="date must be ISO YYYY-MM-DD")
    if d > date.today():
        raise HTTPException(status_code=422, detail="date can't be in the future")
    if d < date(2000, 1, 1):
        raise HTTPException(status_code=422, detail="date too old")
    return d


@router.post("")
async def add_weight(
    user_id: CurrentUserDep, db: DbDep,
    body: dict = Body(...),
):
    weight = body.get("weight")
    if not isinstance(weight, (int, float)) or weight <= 20 or weight > 400:
        raise HTTPException(status_code=422, detail="weight must be 20..400 kg")

    on_date = _parse_date(body.get("date"))

    repo = WeightRepository(db)
    saved = await repo.add_or_update(user_id, float(weight), on_date=on_date)
    return saved


@router.delete("/{on_date}")
async def delete_entry(
    user_id: CurrentUserDep, db: DbDep,
    on_date: str = Path(..., description="ISO date YYYY-MM-DD"),
):
    parsed = _parse_date(on_date)
    if parsed is None:
        raise HTTPException(status_code=422, detail="date is required")
    repo = WeightRepository(db)
    ok = await repo.delete(user_id, parsed)
    if not ok:
        raise HTTPException(status_code=404, detail="entry not found")
    return {"deleted": True, "date": parsed.isoformat()}


# ---------------------------------------------------------------------------
# Forecast helpers
# ---------------------------------------------------------------------------

def _linear_fit(points: list[tuple[float, float]]) -> tuple[float, float] | None:
    """OLS over (x, y). Returns (slope, intercept) or None."""
    n = len(points)
    if n < 2:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    mx = mean(xs)
    my = mean(ys)
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    den = sum((xs[i] - mx) ** 2 for i in range(n))
    if den == 0:
        return None
    slope = num / den
    return slope, my - slope * mx


def _bmr_mifflin(weight_kg: float, height_cm: float, age_years: int, sex: str) -> float:
    """Mifflin-St Jeor — most accurate baseline for healthy adults."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age_years
    if sex.lower().startswith("m") or sex.lower().startswith("м"):
        return base + 5
    return base - 161


async def _user_profile(db, user_id: int) -> dict:
    row = await db.fetchrow(
        """
        SELECT um.user_sex, um.date_of_birth,
               (SELECT height FROM user_health
                 WHERE user_id = um.user_id AND height IS NOT NULL
                 ORDER BY date DESC LIMIT 1) AS height,
               (SELECT user_aim FROM user_aims
                 WHERE user_id = um.user_id LIMIT 1) AS aim
        FROM user_main um
        WHERE um.user_id = $1
        """,
        user_id,
    )
    if not row:
        return {}
    today = date.today()
    age = None
    if row["date_of_birth"]:
        dob = row["date_of_birth"]
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return {
        "sex": (row["user_sex"] or "").strip() or "m",
        "age": age or 30,
        "height_cm": float(row["height"] or 170),
        "activity": "moderate",  # `user_aims` doesn't store this yet → safe default
        "aim": (row["aim"] or "").lower().strip(),
    }


async def _avg_daily_kcal(db, user_id: int, days: int = 14) -> float | None:
    """Average kcal intake over the last `days` days. Skips zero-intake days."""
    row = await db.fetchrow(
        """
        SELECT AVG(daily_total) AS avg_kcal, COUNT(*) AS n
        FROM (
            SELECT date, SUM(cal) AS daily_total
            FROM food
            WHERE user_id = $1
              AND date >= CURRENT_DATE - ($2::int - 1) * INTERVAL '1 day'
              AND cal > 0
            GROUP BY date
            HAVING SUM(cal) > 200  -- ignore "tasted a cracker" days
        ) days_with_food
        """,
        user_id, days,
    )
    if not row or not row["avg_kcal"] or row["n"] < 3:
        return None
    return float(row["avg_kcal"])


def _energy_slope_kg_per_day(avg_kcal: float, tdee: float) -> float:
    """Each KCAL_PER_KG_BODYMASS net-kcal moves the scale by 1 kg.
    Cap to ±0.5 kg/day so a wild outlier day can't blow up projections."""
    raw = (avg_kcal - tdee) / KCAL_PER_KG_BODYMASS
    return max(min(raw, 0.5), -0.5)


@router.get("/forecast")
async def forecast(
    user_id: CurrentUserDep,
    db: DbDep,
    horizon_days: int = Query(30, ge=7, le=180),
    range_: str = Query("30d", alias="range", pattern=r"^(7d|30d|90d|1y|all)$"),
):
    """Forecast endpoint with selectable history range.

    Returns:
        - `points`        – measured history within the requested range
        - `forecast`      – predicted points (`horizon_days` ahead from latest)
        - `trend_kg_per_week` – the **applied** weekly slope (blended)
        - `trend_breakdown`   – fit/energy components for transparency in UI
        - `target_weight`     – derived from user's goal
        - `days_to_target`    – ETA to target at the applied slope, or None
    """
    repo = WeightRepository(db)

    # History always full first, then trimmed to the requested range so the OLS
    # gets the most accurate signal even when the chart shows just 7 days.
    full_hist = await repo.history(user_id, days=3650)
    if not full_hist:
        return {
            "enough_data": False,
            "points": [],
            "forecast": [],
            "trend_kg_per_week": None,
            "trend_breakdown": None,
            "target_weight": await repo.target_weight(user_id),
            "days_to_target": None,
            "range": range_,
            "message": "no_data",
        }

    days_window = RANGE_DAYS[range_]
    if days_window is None:
        windowed = full_hist
    else:
        cutoff = (date.today() - timedelta(days=days_window - 1)).isoformat()
        windowed = [p for p in full_hist if p["date"] >= cutoff]
        if not windowed:
            windowed = [full_hist[-1]]

    target = await repo.target_weight(user_id)
    profile = await _user_profile(db, user_id)
    latest_weight = float(full_hist[-1]["weight"])
    latest_date = date.fromisoformat(full_hist[-1]["date"])

    # --- Empirical fit on full history (most stable) -----------------------
    start_date = date.fromisoformat(full_hist[0]["date"])
    pts_full = [
        (float((date.fromisoformat(p["date"]) - start_date).days), float(p["weight"]))
        for p in full_hist
    ]
    fit = _linear_fit(pts_full)
    fit_slope = fit[0] if fit else None

    # --- Energy-balance projection ----------------------------------------
    energy_slope = None
    tdee = None
    avg_kcal = None
    if profile:
        bmr = _bmr_mifflin(
            weight_kg=latest_weight,
            height_cm=profile["height_cm"],
            age_years=profile["age"],
            sex=profile["sex"],
        )
        af = ACTIVITY_FACTORS.get(profile["activity"], DEFAULT_ACTIVITY)
        tdee = bmr * af
        avg_kcal = await _avg_daily_kcal(db, user_id, days=14)
        if avg_kcal is not None:
            energy_slope = _energy_slope_kg_per_day(avg_kcal, tdee)

    # --- Blend slopes ------------------------------------------------------
    n_history = len(full_hist)
    history_span = (latest_date - start_date).days if n_history >= 2 else 0
    # Confidence in OLS grows with both count and span; saturates around
    # 6 weeks of data, which is when biological noise mostly washes out.
    fit_confidence = min(1.0, max(0.0, (n_history - 3) / 12) * min(1.0, history_span / 42))

    if fit_slope is not None and energy_slope is not None:
        applied_slope = fit_confidence * fit_slope + (1 - fit_confidence) * energy_slope
        method = "blend"
    elif fit_slope is not None:
        applied_slope = fit_slope
        method = "fit"
    elif energy_slope is not None:
        applied_slope = energy_slope
        method = "energy"
    else:
        applied_slope = 0.0
        method = "flat"

    # --- Build forecast points --------------------------------------------
    fc: list[dict] = []
    for offset in range(1, horizon_days + 1):
        proj_date = latest_date + timedelta(days=offset)
        proj_weight = latest_weight + applied_slope * offset
        # Hard physical bounds — nobody loses 50 kg in a month.
        proj_weight = max(35.0, min(300.0, proj_weight))
        fc.append({"date": proj_date.isoformat(), "weight": round(proj_weight, 2)})

    # --- ETA to target -----------------------------------------------------
    days_to_target = None
    if target is not None and abs(applied_slope) > 1e-4:
        if (applied_slope < 0 and target < latest_weight) or (
            applied_slope > 0 and target > latest_weight
        ):
            d_need = (target - latest_weight) / applied_slope
            if 0 < d_need <= 365 * 3:
                days_to_target = int(round(d_need))

    return {
        "enough_data": n_history >= 3,
        "points": windowed,
        "forecast": fc,
        "trend_kg_per_week": round(applied_slope * 7, 3),
        "trend_breakdown": {
            "method": method,
            "fit_kg_per_week": round(fit_slope * 7, 3) if fit_slope is not None else None,
            "energy_kg_per_week": round(energy_slope * 7, 3) if energy_slope is not None else None,
            "fit_confidence": round(fit_confidence, 3),
            "tdee_kcal": round(tdee) if tdee else None,
            "avg_kcal": round(avg_kcal) if avg_kcal else None,
        },
        "target_weight": target,
        "days_to_target": days_to_target,
        "latest_weight": round(latest_weight, 2),
        "latest_date": full_hist[-1]["date"],
        "range": range_,
    }
