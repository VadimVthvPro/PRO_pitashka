import logging
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Query

from app.dependencies import DbDep, CurrentUserDep, RedisDep
from app.services import ai_service, quota_service
from app.services.quota_service import QuotaExceeded
from app.services.ai_service import (
    AIConfigError,
    AIQuotaError,
    AITimeoutError,
    AIUpstreamError,
)
from app.services.cache_service import CacheService
from app.config import get_settings
from app.repositories.weight_repo import WeightRepository

logger = logging.getLogger(__name__)
router = APIRouter()


async def _collect_week_stats(db, user_id: int) -> dict:
    today = date.today()
    week_start = today - timedelta(days=6)

    food_row = await db.fetchrow(
        """
        SELECT
            COALESCE(SUM(cal), 0) AS cal,
            COALESCE(SUM(b), 0) AS protein,
            COALESCE(SUM(g), 0) AS fat,
            COALESCE(SUM(u), 0) AS carbs,
            COUNT(DISTINCT date)::int AS days_logged,
            COUNT(*)::int AS entries
        FROM food
        WHERE user_id = $1 AND date BETWEEN $2 AND $3
        """,
        user_id, week_start, today,
    )

    water_row = await db.fetchrow(
        """
        SELECT
            COALESCE(SUM(count), 0)::int AS glasses,
            COUNT(*)::int AS days_logged
        FROM water
        WHERE user_id = $1 AND date BETWEEN $2 AND $3
        """,
        user_id, week_start, today,
    )

    workout_row = await db.fetchrow(
        """
        SELECT
            COUNT(*)::int AS sessions,
            COALESCE(SUM(tren_time), 0)::int AS minutes,
            COALESCE(SUM(training_cal), 0)::int AS cal_burned
        FROM user_training
        WHERE user_id = $1 AND date BETWEEN $2 AND $3
        """,
        user_id, week_start, today,
    )

    aims_row = await db.fetchrow(
        "SELECT user_aim, daily_cal FROM user_aims WHERE user_id = $1", user_id
    )

    weight_repo = WeightRepository(db)
    weight_hist = await weight_repo.history(user_id, days=14)

    return {
        "period": {"from": week_start.isoformat(), "to": today.isoformat()},
        "goal": (aims_row["user_aim"] if aims_row else None),
        "daily_cal_target": (int(aims_row["daily_cal"]) if aims_row and aims_row["daily_cal"] else None),
        "food": {
            "total_cal": int(food_row["cal"] or 0),
            "avg_daily_cal": int((food_row["cal"] or 0) / 7),
            "days_logged": food_row["days_logged"],
            "entries": food_row["entries"],
            "protein_g": float(food_row["protein"] or 0),
            "fat_g": float(food_row["fat"] or 0),
            "carbs_g": float(food_row["carbs"] or 0),
        },
        "water": {
            "glasses_total": water_row["glasses"],
            "days_logged": water_row["days_logged"],
            "avg_daily": round((water_row["glasses"] or 0) / 7, 1),
        },
        "workouts": {
            "sessions": workout_row["sessions"],
            "minutes": workout_row["minutes"],
            "cal_burned": workout_row["cal_burned"],
        },
        "weight_recent": weight_hist[-5:],
    }


@router.get("/weekly")
async def weekly(
    user_id: CurrentUserDep, db: DbDep, redis: RedisDep,
    refresh: bool = Query(default=False, description="Skip cache and re-generate"),
):
    settings = get_settings()
    cache = CacheService(redis, settings.CACHE_ENABLED)
    from app.repositories.user_repo import UserRepository
    lang = await UserRepository(db).get_lang(user_id) or "ru"
    cache_key = f"digest:weekly:{lang}:{user_id}:{date.today().isoformat()}"

    if not refresh:
        cached = await cache.get(cache_key)
        if cached:
            return cached

    stats = await _collect_week_stats(db, user_id)

    # Дайджест — платная фича по квоте. Бесплатным даём 1/мес, но, если
    # кэш уже прогрет (выше), юзер бесплатно получает тот же результат до
    # конца дня. Квоту списываем ТОЛЬКО при новом запросе к AI.
    try:
        await quota_service.consume(db, redis, user_id, "ai_digest")
    except QuotaExceeded as exc:
        st = exc.status
        raise HTTPException(
            status_code=402,
            detail={
                "code": "quota_exceeded", "message": exc.message,
                "plan_key": st.plan_key, "tier": st.tier, "quota_key": st.key,
                "limit": st.limit, "used": st.used,
                "reset_at": st.reset_at.isoformat() if st.reset_at else None,
                "upgrade": {"suggested_plan_key": "premium_month" if st.tier == "free" else "pro_month",
                            "billing_url": "/billing"},
            },
        )

    if stats["food"]["entries"] == 0 and stats["workouts"]["sessions"] == 0 and stats["water"]["glasses_total"] == 0:
        return {
            "stats": stats,
            "digest": None,
            "source": None,
            "message": "Ещё мало данных — добавь еду, воду или тренировку, чтобы я собрал дайджест",
        }

    digest: dict
    source: str
    ai_error: str | None = None
    try:
        digest = await ai_service.weekly_digest(stats, lang=lang)
        source = "ai"
    except AIConfigError as e:
        logger.warning("weekly_digest: AI misconfigured (%s)", e)
        digest = _fallback_digest(stats)
        source = "fallback"
        ai_error = "ai_misconfigured"
    except AIQuotaError as e:
        logger.warning("weekly_digest: AI quota (%s)", e)
        digest = _fallback_digest(stats)
        source = "fallback"
        ai_error = "ai_quota_exceeded"
    except AITimeoutError as e:
        logger.warning("weekly_digest: AI timeout (%s)", e)
        digest = _fallback_digest(stats)
        source = "fallback"
        ai_error = "ai_timeout"
    except AIUpstreamError as e:
        logger.warning("weekly_digest: AI upstream error (%s)", e)
        digest = _fallback_digest(stats)
        source = "fallback"
        ai_error = "ai_unavailable"
    except Exception as e:
        logger.warning("weekly_digest: AI error (%s)", e)
        digest = _fallback_digest(stats)
        source = "fallback"
        ai_error = "ai_unavailable"

    payload = {"stats": stats, "digest": digest, "source": source}
    if ai_error:
        payload["ai_error"] = ai_error

    # Cache AI digests for an hour. Cache fallbacks for only 5 minutes so AI
    # can be retried as soon as the upstream issue resolves.
    await cache.set(cache_key, payload, 3600 if source == "ai" else 300)
    return payload


def _fallback_digest(stats: dict) -> dict:
    """Deterministic digest if AI is unavailable (quota, rate limit)."""
    food = stats["food"]
    water = stats["water"]
    work = stats["workouts"]
    target = stats.get("daily_cal_target")

    wins, focus = [], []
    if food["days_logged"] >= 6:
        wins.append(f"Записал еду {food['days_logged']} из 7 дней — железная дисциплина")
    elif food["days_logged"] >= 3:
        wins.append(f"Запись еды за {food['days_logged']} дней — хорошая база")
    else:
        focus.append("Попробуй записывать еду хотя бы 5 дней в неделю")

    if water["avg_daily"] >= 7:
        wins.append(f"Вода в норме: {water['avg_daily']} стаканов в среднем")
    elif water["glasses_total"] < 20:
        focus.append("Вода — слабое место. Цель 8 стаканов в день")

    if work["sessions"] >= 3:
        wins.append(f"{work['sessions']} тренировок — отличный темп")
    elif work["sessions"] == 0:
        focus.append("За неделю ни одной тренировки. Начни с 20 минут ходьбы")
    else:
        focus.append("Добавь ещё 1-2 коротких тренировки")

    if target and food["avg_daily_cal"] > 0:
        gap = food["avg_daily_cal"] - target
        if abs(gap) < 150:
            wins.append(f"Средние {food['avg_daily_cal']} ккал/день — почти в цель")
        elif gap > 150:
            focus.append(f"В среднем на {gap} ккал больше нормы")
        else:
            focus.append(f"В среднем на {abs(gap)} ккал меньше нормы")

    summary = (
        f"За неделю: {food['days_logged']} дней с едой, "
        f"{water['glasses_total']} стаканов воды, "
        f"{work['sessions']} тренировок."
    )
    tip = "Лучший прогресс приходит от мелких постоянных привычек. Выбери одну из точек роста — и работай над ней 7 дней."

    return {
        "summary": summary,
        "wins": wins[:3],
        "focus": focus[:3],
        "tip": tip,
    }
