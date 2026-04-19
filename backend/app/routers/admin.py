import hashlib
import hmac
import secrets
from typing import Optional

from fastapi import APIRouter, Body, Cookie, HTTPException, Query, Request, Response
from app.config import get_settings
from app.dependencies import DbDep, CurrentUserDep
from app.repositories.admin_repo import AdminRepository

router = APIRouter()

ALLOWED_TABLES = {
    "user_main", "user_lang", "user_health", "user_aims",
    "food", "water", "user_training", "training_types",
    "training_coefficients", "chat_history", "admin_users",
    "web_sessions", "otp_codes", "user_settings",
    "audit_log", "social_posts", "social_likes", "social_follows",
}

ADMIN_COOKIE_NAME = "admin_panel_token"
ADMIN_COOKIE_TTL = 8 * 3600  # seconds


def _admin_token_value() -> str:
    """Stable, environment-bound token derived from ADMIN_PASSWORD.

    We don't store sessions in DB — the token itself is an HMAC of the password
    with the JWT secret. Verifying = recompute and constant-time compare.
    """
    settings = get_settings()
    if not settings.ADMIN_PASSWORD:
        return ""
    return hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        settings.ADMIN_PASSWORD.encode(),
        hashlib.sha256,
    ).hexdigest()


def _is_admin_cookie_valid(token: Optional[str]) -> bool:
    expected = _admin_token_value()
    if not token or not expected:
        return False
    return hmac.compare_digest(token, expected)


async def _check_admin(user_id: int, db, request: Request | None = None) -> None:
    """Two acceptable proofs of admin:

    1. Old: telegram_username appears in admin_users (legacy bot admins).
    2. New: cookie `admin_panel_token` matches HMAC(ADMIN_PASSWORD).
    """
    if request is not None and _is_admin_cookie_valid(request.cookies.get(ADMIN_COOKIE_NAME)):
        return
    row = await db.fetchrow(
        "SELECT id FROM admin_users au "
        "JOIN user_main um ON LOWER(au.username) = um.telegram_username "
        "WHERE um.user_id = $1",
        user_id,
    )
    if not row:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.post("/login")
async def admin_login(response: Response, body: dict = Body(...)):
    """Verify ADMIN_PASSWORD; on success, set httpOnly cookie for 8h."""
    settings = get_settings()
    if not settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="ADMIN_PASSWORD is not configured")
    provided = (body or {}).get("password") or ""
    if not hmac.compare_digest(provided, settings.ADMIN_PASSWORD):
        # Constant work even on failure.
        secrets.token_hex(8)
        raise HTTPException(status_code=401, detail="Invalid password")
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=_admin_token_value(),
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=ADMIN_COOKIE_TTL,
        path="/",
    )
    return {"ok": True, "expires_in": ADMIN_COOKIE_TTL}


@router.post("/logout")
async def admin_logout(response: Response):
    response.delete_cookie(ADMIN_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/session")
async def admin_session(request: Request):
    valid = _is_admin_cookie_valid(request.cookies.get(ADMIN_COOKIE_NAME))
    return {"authorized": valid, "configured": bool(get_settings().ADMIN_PASSWORD)}


async def _admin_or_password(request: Request, user_id: int | None, db) -> None:
    """Either logged-in user is in admin_users OR admin password cookie is set."""
    if _is_admin_cookie_valid(request.cookies.get(ADMIN_COOKIE_NAME)):
        return
    if user_id is None:
        raise HTTPException(status_code=401, detail="Auth required")
    await _check_admin(user_id, db, request)


async def _try_user_id(request: Request) -> int | None:
    """Best-effort current user id without raising — admin cookie may be enough."""
    from app.dependencies import get_current_user_id
    try:
        return await get_current_user_id(request, get_settings())
    except HTTPException:
        return None


@router.get("/tables")
async def list_tables(request: Request, db: DbDep):
    user_id = await _try_user_id(request)
    await _admin_or_password(request, user_id, db)
    repo = AdminRepository(db)
    tables = await repo.list_tables()
    return {"tables": [t for t in tables if t in ALLOWED_TABLES]}


@router.get("/tables/{table_name}")
async def get_table_data(
    table_name: str, request: Request, db: DbDep,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=200),
):
    user_id = await _try_user_id(request)
    await _admin_or_password(request, user_id, db)
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail="Table not found")

    repo = AdminRepository(db)
    columns = await repo.get_table_columns(table_name)
    offset = (page - 1) * per_page
    rows = await repo.get_rows(table_name, per_page, offset)
    total = await repo.count_rows(table_name)
    return {
        "columns": columns,
        "rows": rows,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.delete("/tables/{table_name}/{pk_column}/{pk_value}")
async def delete_row(
    table_name: str, pk_column: str, pk_value: str,
    request: Request, db: DbDep,
):
    user_id = await _try_user_id(request)
    await _admin_or_password(request, user_id, db)
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail="Table not found")

    repo = AdminRepository(db)

    columns = await repo.get_table_columns(table_name)
    valid_columns = {c["column_name"] for c in columns}
    if pk_column not in valid_columns:
        raise HTTPException(status_code=400, detail=f"Invalid column: {pk_column}")

    try:
        typed_value: int | str = int(pk_value)
    except ValueError:
        typed_value = pk_value

    deleted = await repo.delete_row(table_name, pk_column, typed_value)
    if not deleted:
        raise HTTPException(status_code=404, detail="Row not found")
    return {"message": "Deleted"}


# ---------------------------------------------------------------------------
# Overview — high-level dashboard for the admin landing screen.
# All numbers come from real tables; nothing is mocked.
# ---------------------------------------------------------------------------


@router.get("/overview")
async def admin_overview(request: Request, db: DbDep):
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)

    # --- users -------------------------------------------------------------
    users_total = await db.fetchval("SELECT COUNT(*) FROM user_main")
    users_today = await db.fetchval(
        "SELECT COUNT(*) FROM user_main WHERE created_at >= NOW() - INTERVAL '1 day'"
    )
    users_week = await db.fetchval(
        "SELECT COUNT(*) FROM user_main WHERE created_at >= NOW() - INTERVAL '7 days'"
    )
    # active = at least one audit-log entry in window
    active_24h = await db.fetchval(
        "SELECT COUNT(DISTINCT user_id) FROM audit_log "
        "WHERE user_id IS NOT NULL AND created_at >= NOW() - INTERVAL '1 day'"
    )
    active_7d = await db.fetchval(
        "SELECT COUNT(DISTINCT user_id) FROM audit_log "
        "WHERE user_id IS NOT NULL AND created_at >= NOW() - INTERVAL '7 days'"
    )

    # --- food / water / training (today) -----------------------------------
    food_today = await db.fetchrow(
        "SELECT COUNT(*) AS rows, COALESCE(SUM(cal),0)::int AS cal "
        "FROM food WHERE date = CURRENT_DATE"
    )
    water_today = await db.fetchval(
        "SELECT COALESCE(SUM(count),0)::int FROM water WHERE date = CURRENT_DATE"
    )
    training_today = await db.fetchrow(
        "SELECT COUNT(*) AS rows, COALESCE(SUM(training_cal),0)::int AS cal "
        "FROM user_training WHERE date = CURRENT_DATE"
    )

    # --- AI usage (last 7 days) -------------------------------------------
    ai_rows = await db.fetch(
        """
        SELECT category, COUNT(*) AS cnt,
               SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) AS errs
        FROM audit_log
        WHERE created_at >= NOW() - INTERVAL '7 days'
          AND category LIKE 'ai_%'
        GROUP BY category
        ORDER BY cnt DESC
        """
    )

    # --- social ------------------------------------------------------------
    social_posts = await db.fetchval("SELECT COUNT(*) FROM social_posts")
    social_posts_week = await db.fetchval(
        "SELECT COUNT(*) FROM social_posts WHERE created_at >= NOW() - INTERVAL '7 days'"
    )
    social_likes = await db.fetchval("SELECT COUNT(*) FROM social_likes")

    # --- top users by recent activity -------------------------------------
    top_users = await db.fetch(
        """
        SELECT al.user_id,
               um.name,
               um.telegram_username,
               COUNT(*) AS actions
        FROM audit_log al
        JOIN user_main um ON um.user_id = al.user_id
        WHERE al.created_at >= NOW() - INTERVAL '7 days'
          AND al.user_id IS NOT NULL
        GROUP BY al.user_id, um.name, um.telegram_username
        ORDER BY actions DESC
        LIMIT 10
        """
    )

    # --- recent errors -----------------------------------------------------
    recent_errors = await db.fetch(
        """
        SELECT id, user_id, method, path, status_code, created_at, detail
        FROM audit_log
        WHERE status_code >= 500
        ORDER BY created_at DESC
        LIMIT 10
        """
    )

    return {
        "users": {
            "total": int(users_total or 0),
            "new_today": int(users_today or 0),
            "new_week": int(users_week or 0),
            "active_24h": int(active_24h or 0),
            "active_7d": int(active_7d or 0),
        },
        "today": {
            "food_entries": int(food_today["rows"] or 0),
            "food_calories": int(food_today["cal"] or 0),
            "water_glasses": int(water_today or 0),
            "training_entries": int(training_today["rows"] or 0),
            "training_calories": int(training_today["cal"] or 0),
        },
        "ai_7d": [
            {
                "category": r["category"],
                "count": int(r["cnt"]),
                "errors": int(r["errs"] or 0),
            }
            for r in ai_rows
        ],
        "social": {
            "posts": int(social_posts or 0),
            "posts_week": int(social_posts_week or 0),
            "likes": int(social_likes or 0),
        },
        "top_users": [
            {
                "user_id": r["user_id"],
                "name": r["name"],
                "telegram_username": r["telegram_username"],
                "actions": int(r["actions"]),
            }
            for r in top_users
        ],
        "recent_errors": [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "method": r["method"],
                "path": r["path"],
                "status_code": r["status_code"],
                "detail": dict(r["detail"] or {}),
                "created_at": r["created_at"].isoformat(),
            }
            for r in recent_errors
        ],
    }


# ---------------------------------------------------------------------------
# Audit log viewer
# ---------------------------------------------------------------------------

AUDIT_CATEGORIES = [
    "ai_food", "ai_workout", "ai_chat", "ai_digest", "ai_other",
    "food", "workouts", "water", "weight",
    "auth", "settings", "profile", "social", "admin",
    "streaks", "summary", "other",
]


@router.get("/audit")
async def audit_list(
    request: Request,
    db: DbDep,
    category: Optional[str] = Query(None),
    user_id_filter: Optional[int] = Query(None, alias="user_id"),
    method: Optional[str] = Query(None),
    status_min: int = Query(0, ge=0, le=599),
    status_max: int = Query(599, ge=0, le=599),
    search: Optional[str] = Query(None, description="Substring of path"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)

    where = ["status_code >= $1", "status_code <= $2"]
    args: list = [status_min, status_max]
    if category:
        args.append(category)
        where.append(f"category = ${len(args)}")
    if user_id_filter is not None:
        args.append(user_id_filter)
        where.append(f"user_id = ${len(args)}")
    if method:
        args.append(method.upper())
        where.append(f"method = ${len(args)}")
    if search:
        args.append(f"%{search}%")
        where.append(f"path ILIKE ${len(args)}")

    args.extend([limit, offset])
    rows = await db.fetch(
        f"""
        SELECT id, user_id, method, path, category, status_code,
               duration_ms, ip, user_agent, detail, created_at
        FROM audit_log
        WHERE {' AND '.join(where)}
        ORDER BY created_at DESC
        LIMIT ${len(args) - 1} OFFSET ${len(args)}
        """,
        *args,
    )
    total = await db.fetchval(
        f"SELECT COUNT(*) FROM audit_log WHERE {' AND '.join(where[:len(where)])}",
        *args[:-2],
    )
    return {
        "items": [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "method": r["method"],
                "path": r["path"],
                "category": r["category"],
                "status_code": r["status_code"],
                "duration_ms": r["duration_ms"],
                "ip": str(r["ip"]) if r["ip"] else None,
                "user_agent": r["user_agent"],
                "detail": dict(r["detail"] or {}),
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ],
        "total": int(total or 0),
        "categories": AUDIT_CATEGORIES,
    }


@router.get("/audit/stats")
async def audit_stats(request: Request, db: DbDep, days: int = Query(7, ge=1, le=90)):
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)
    # `INTERVAL '1 day' * $1` avoids brittle text concat that some pg versions
    # rejected with "operator does not exist: integer || unknown".
    rows = await db.fetch(
        """
        SELECT category, COUNT(*) AS cnt
        FROM audit_log
        WHERE created_at >= NOW() - (INTERVAL '1 day') * $1
        GROUP BY category
        ORDER BY cnt DESC
        """,
        days,
    )
    daily = await db.fetch(
        """
        SELECT date_trunc('day', created_at) AS day, COUNT(*) AS cnt
        FROM audit_log
        WHERE created_at >= NOW() - (INTERVAL '1 day') * $1
        GROUP BY day
        ORDER BY day
        """,
        days,
    )
    totals = await db.fetchrow(
        """
        SELECT
          COUNT(*)                               AS total,
          COUNT(DISTINCT user_id)                AS uniq_users,
          COALESCE(AVG(duration_ms), 0)::int     AS avg_ms,
          SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) AS errors_5xx,
          SUM(CASE WHEN status_code BETWEEN 400 AND 499 THEN 1 ELSE 0 END) AS errors_4xx
        FROM audit_log
        WHERE created_at >= NOW() - (INTERVAL '1 day') * $1
        """,
        days,
    )
    return {
        "by_category": [{"category": r["category"], "count": int(r["cnt"])} for r in rows],
        "by_day": [
            {"day": r["day"].date().isoformat(), "count": int(r["cnt"])}
            for r in daily
        ],
        "totals": {
            "total": int(totals["total"] or 0),
            "uniq_users": int(totals["uniq_users"] or 0),
            "avg_ms": int(totals["avg_ms"] or 0),
            "errors_5xx": int(totals["errors_5xx"] or 0),
            "errors_4xx": int(totals["errors_4xx"] or 0),
        },
    }


# ---------------------------------------------------------------------------
# Users overview
# ---------------------------------------------------------------------------

@router.get("/users")
async def admin_users_list(
    request: Request,
    db: DbDep,
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)

    args: list = []
    where = ""
    if search:
        args.append(f"%{search.lower()}%")
        where = (
            "WHERE LOWER(COALESCE(name,'')) LIKE $1 "
            "OR LOWER(COALESCE(telegram_username,'')) LIKE $1 "
            "OR LOWER(COALESCE(google_email,'')) LIKE $1"
        )

    args.extend([limit, offset])
    rows = await db.fetch(
        f"""
        SELECT user_id, name, telegram_username, google_email,
               created_at, social_score
        FROM user_main
        {where}
        ORDER BY user_id DESC
        LIMIT ${len(args) - 1} OFFSET ${len(args)}
        """,
        *args,
    )
    total = await db.fetchval(
        f"SELECT COUNT(*) FROM user_main {where}",
        *args[:-2],
    )

    return {
        "items": [dict(r) for r in rows],
        "total": int(total or 0),
    }


@router.get("/users/{target_id}")
async def admin_user_detail(target_id: int, request: Request, db: DbDep):
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)

    user = await db.fetchrow("SELECT * FROM user_main WHERE user_id = $1", target_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    health = await db.fetch(
        "SELECT date, weight, height, imt FROM user_health "
        "WHERE user_id = $1 ORDER BY date DESC LIMIT 30",
        target_id,
    )
    recent = await db.fetch(
        """
        SELECT method, path, category, status_code, created_at
        FROM audit_log WHERE user_id = $1
        ORDER BY created_at DESC LIMIT 50
        """,
        target_id,
    )
    return {
        "user": dict(user),
        "health": [dict(r) for r in health],
        "recent_actions": [
            {**dict(r), "created_at": r["created_at"].isoformat()} for r in recent
        ],
    }
