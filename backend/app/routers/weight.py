from datetime import date, timedelta
from statistics import mean
from fastapi import APIRouter, Body, HTTPException, Query

from app.dependencies import DbDep, CurrentUserDep
from app.repositories.weight_repo import WeightRepository

router = APIRouter()


@router.get("/history")
async def history(user_id: CurrentUserDep, db: DbDep, days: int = Query(default=90, ge=7, le=365)):
    repo = WeightRepository(db)
    items = await repo.history(user_id, days)
    return {"items": items, "days": days}


@router.post("")
async def add_weight(
    user_id: CurrentUserDep, db: DbDep,
    body: dict = Body(...),
):
    weight = body.get("weight")
    if not isinstance(weight, (int, float)) or weight <= 20 or weight > 400:
        raise HTTPException(status_code=422, detail="weight must be 20..400 kg")

    repo = WeightRepository(db)
    saved = await repo.add_or_update(user_id, float(weight))
    return saved


def _linear_fit(points: list[tuple[float, float]]) -> tuple[float, float] | None:
    """Plain least-squares: returns (slope, intercept) over (x, y)."""
    n = len(points)
    if n < 3:
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
    intercept = my - slope * mx
    return slope, intercept


@router.get("/forecast")
async def forecast(user_id: CurrentUserDep, db: DbDep, horizon_days: int = 30):
    repo = WeightRepository(db)
    hist = await repo.history(user_id, days=90)
    if len(hist) < 3:
        return {
            "enough_data": False,
            "points": hist,
            "forecast": [],
            "trend_kg_per_week": None,
            "target_weight": await repo.target_weight(user_id),
            "days_to_target": None,
            "message": "Добавь хотя бы 3 записи веса — построю тренд",
        }

    start_date = date.fromisoformat(hist[0]["date"])
    points = [(float((date.fromisoformat(p["date"]) - start_date).days), float(p["weight"])) for p in hist]
    fit = _linear_fit(points)
    target = await repo.target_weight(user_id)

    if not fit:
        return {
            "enough_data": False,
            "points": hist,
            "forecast": [],
            "trend_kg_per_week": None,
            "target_weight": target,
            "days_to_target": None,
            "message": "Пока нужен более стабильный тренд",
        }

    slope, intercept = fit
    trend_per_week = slope * 7

    latest_day = points[-1][0]
    fc = []
    today = date.today()
    for d in range(1, horizon_days + 1):
        x = latest_day + d
        y = intercept + slope * x
        fc_date = (start_date + timedelta(days=int(x))).isoformat()
        # Stop forecasting when date would exceed logical bounds
        fc.append({"date": fc_date, "weight": round(y, 2)})

    days_to_target = None
    if target is not None and slope != 0:
        latest_weight = points[-1][1]
        if (slope < 0 and target < latest_weight) or (slope > 0 and target > latest_weight):
            d_need = (target - intercept) / slope - latest_day
            if d_need > 0:
                days_to_target = int(round(d_need))
                # Sanity cap
                if days_to_target > 365 * 3:
                    days_to_target = None

    return {
        "enough_data": True,
        "points": hist,
        "forecast": fc,
        "trend_kg_per_week": round(trend_per_week, 3),
        "target_weight": target,
        "days_to_target": days_to_target,
        "latest_weight": round(points[-1][1], 2),
        "latest_date": hist[-1]["date"],
    }
