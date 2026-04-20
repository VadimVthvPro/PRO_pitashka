import hashlib
import hmac
import json
import secrets
from typing import Any, Optional

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


def _safe_detail(value: Any) -> dict:
    """Audit `detail` is JSONB; asyncpg returns it as raw text.

    Older callers wrote dicts directly, newer ones serialise to a string,
    and migrations leave NULLs. Coerce all of these into a plain dict so
    the response stays predictable for the frontend.
    """
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except Exception:
            return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except Exception:
            return {"raw": value}
    return {"value": value}


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
               um.user_name AS name,
               um.telegram_username,
               COUNT(*) AS actions
        FROM audit_log al
        JOIN user_main um ON um.user_id = al.user_id
        WHERE al.created_at >= NOW() - INTERVAL '7 days'
          AND al.user_id IS NOT NULL
        GROUP BY al.user_id, um.user_name, um.telegram_username
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
                "detail": _safe_detail(r["detail"]),
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
                "detail": _safe_detail(r["detail"]),
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
            "WHERE LOWER(COALESCE(user_name,'')) LIKE $1 "
            "OR LOWER(COALESCE(telegram_username,'')) LIKE $1 "
            "OR LOWER(COALESCE(google_email,'')) LIKE $1"
        )

    args.extend([limit, offset])
    rows = await db.fetch(
        f"""
        SELECT user_id, user_name AS name, telegram_username, google_email,
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


# ---------------------------------------------------------------------------
# AI chat log: paired user→assistant turns across the whole user base.
# ---------------------------------------------------------------------------


@router.get("/ai/log")
async def admin_ai_log(
    request: Request,
    db: DbDep,
    search: Optional[str] = Query(None, description="Substring of either side of the dialog"),
    target_user: Optional[int] = Query(None, alias="user_id"),
    days: int = Query(7, ge=1, le=365),
    only_negative: bool = Query(False, description="Only assistant replies thumbed-down"),
    has_attach: Optional[str] = Query(None, pattern=r"^(meal_plan|workout_plan|any)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return paired (user → assistant) turns, newest first.

    Pairing strategy: walk chat_history ordered by ``(user_id, created_at)``
    with ``LAG()`` so each assistant row sees the user message that came right
    before it from the same user. Then we filter to assistant rows only and
    keep the lagged ``user_message`` alongside.

    This is robust against gaps (system messages, deleted rows) because we
    only require that the previous message of the same user was a user turn —
    if it wasn't, the pair is dropped.
    """
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)

    where = ["h.message_type = 'assistant'", "h.created_at >= NOW() - (INTERVAL '1 day') * $1"]
    args: list[Any] = [days]
    if target_user is not None:
        args.append(target_user)
        where.append(f"h.user_id = ${len(args)}")
    if only_negative:
        where.append("h.feedback = -1")
    if has_attach == "any":
        where.append("h.attach_kind IS NOT NULL")
    elif has_attach in ("meal_plan", "workout_plan"):
        args.append(has_attach)
        where.append(f"h.attach_kind = ${len(args)}")
    if search:
        args.append(f"%{search.lower()}%")
        where.append(
            f"(LOWER(h.message_text) LIKE ${len(args)} OR LOWER(h.prev_user) LIKE ${len(args)})"
        )

    base_cte = """
        WITH paired AS (
            SELECT
                ch.id,
                ch.user_id,
                ch.message_type,
                ch.message_text,
                ch.created_at,
                ch.feedback,
                ch.attach_kind,
                ch.latency_ms,
                ch.model,
                LAG(ch.message_text) OVER w  AS prev_user,
                LAG(ch.id) OVER w            AS prev_user_id,
                LAG(ch.message_type) OVER w  AS prev_type
            FROM chat_history ch
            WINDOW w AS (PARTITION BY ch.user_id ORDER BY ch.created_at)
        )
    """
    common_where = " AND ".join(where) + " AND h.prev_type = 'user'"

    args_with_paging = [*args, limit, offset]
    rows = await db.fetch(
        f"""
        {base_cte}
        SELECT h.*, um.user_name, um.telegram_username
        FROM paired h
        LEFT JOIN user_main um ON um.user_id = h.user_id
        WHERE {common_where}
        ORDER BY h.created_at DESC
        LIMIT ${len(args_with_paging) - 1} OFFSET ${len(args_with_paging)}
        """,
        *args_with_paging,
    )
    total = await db.fetchval(
        f"""
        {base_cte}
        SELECT COUNT(*) FROM paired h WHERE {common_where}
        """,
        *args,
    )

    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "user_id": r["user_id"],
            "user_name": r["user_name"],
            "telegram_username": r["telegram_username"],
            "user_message": r["prev_user"] or "",
            "user_message_id": r["prev_user_id"],
            "assistant_message": r["message_text"] or "",
            "feedback": r["feedback"],
            "attach_kind": r["attach_kind"],
            "latency_ms": r["latency_ms"],
            "model": r["model"],
            "created_at": r["created_at"].isoformat(),
        })
    return {"items": items, "total": int(total or 0)}


@router.get("/ai/stats")
async def admin_ai_stats(request: Request, db: DbDep, days: int = Query(30, ge=1, le=365)):
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)

    totals = await db.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE message_type = 'assistant')                            AS replies,
            COUNT(*) FILTER (WHERE message_type = 'user')                                 AS questions,
            COUNT(DISTINCT user_id) FILTER (WHERE message_type = 'assistant')             AS uniq_users,
            COALESCE(AVG(LENGTH(message_text))
                     FILTER (WHERE message_type = 'assistant'), 0)::int                   AS avg_reply_chars,
            COALESCE(AVG(latency_ms)
                     FILTER (WHERE message_type = 'assistant' AND latency_ms IS NOT NULL), 0)::int
                                                                                          AS avg_latency_ms,
            COUNT(*) FILTER (WHERE feedback = 1)                                          AS thumbs_up,
            COUNT(*) FILTER (WHERE feedback = -1)                                         AS thumbs_down,
            COUNT(*) FILTER (WHERE message_type = 'assistant'
                              AND created_at >= NOW() - INTERVAL '1 day')                 AS replies_24h
        FROM chat_history
        WHERE created_at >= NOW() - (INTERVAL '1 day') * $1
        """,
        days,
    )
    by_day = await db.fetch(
        """
        SELECT date_trunc('day', created_at)::date AS day,
               COUNT(*) FILTER (WHERE message_type = 'assistant') AS replies,
               COUNT(*) FILTER (WHERE message_type = 'user')      AS questions
        FROM chat_history
        WHERE created_at >= NOW() - (INTERVAL '1 day') * $1
        GROUP BY day
        ORDER BY day
        """,
        days,
    )
    top_users = await db.fetch(
        """
        SELECT ch.user_id,
               COALESCE(um.user_name, um.telegram_username, 'user') AS name,
               um.telegram_username,
               COUNT(*) FILTER (WHERE ch.message_type = 'assistant') AS replies
        FROM chat_history ch
        LEFT JOIN user_main um ON um.user_id = ch.user_id
        WHERE ch.created_at >= NOW() - (INTERVAL '1 day') * $1
        GROUP BY ch.user_id, um.user_name, um.telegram_username
        HAVING COUNT(*) FILTER (WHERE ch.message_type = 'assistant') > 0
        ORDER BY replies DESC
        LIMIT 10
        """,
        days,
    )
    by_attach = await db.fetch(
        """
        SELECT COALESCE(attach_kind, 'none') AS kind,
               COUNT(*) AS cnt,
               COUNT(*) FILTER (WHERE feedback = 1)  AS up,
               COUNT(*) FILTER (WHERE feedback = -1) AS down
        FROM chat_history
        WHERE message_type = 'assistant'
          AND created_at >= NOW() - (INTERVAL '1 day') * $1
        GROUP BY kind
        ORDER BY cnt DESC
        """,
        days,
    )
    return {
        "totals": {
            "replies": int(totals["replies"] or 0),
            "questions": int(totals["questions"] or 0),
            "uniq_users": int(totals["uniq_users"] or 0),
            "avg_reply_chars": int(totals["avg_reply_chars"] or 0),
            "avg_latency_ms": int(totals["avg_latency_ms"] or 0),
            "thumbs_up": int(totals["thumbs_up"] or 0),
            "thumbs_down": int(totals["thumbs_down"] or 0),
            "replies_24h": int(totals["replies_24h"] or 0),
        },
        "by_day": [
            {"day": r["day"].isoformat(),
             "replies": int(r["replies"] or 0),
             "questions": int(r["questions"] or 0)}
            for r in by_day
        ],
        "top_users": [
            {"user_id": r["user_id"],
             "name": r["name"],
             "telegram_username": r["telegram_username"],
             "replies": int(r["replies"])}
            for r in top_users
        ],
        "by_attach": [
            {"kind": r["kind"],
             "count": int(r["cnt"]),
             "up": int(r["up"] or 0),
             "down": int(r["down"] or 0)}
            for r in by_attach
        ],
    }


@router.delete("/ai/message/{message_id}")
async def admin_delete_ai_message(message_id: int, request: Request, db: DbDep):
    """Hard-delete a chat message (admin moderation tool).

    Logs to audit_log so the action is traceable. Used when an assistant
    reply is unsafe/PII-leaking and needs to disappear from a user's history.
    """
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)
    row = await db.fetchrow(
        "SELECT id, user_id, message_type FROM chat_history WHERE id = $1",
        message_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="message not found")
    await db.execute("DELETE FROM chat_history WHERE id = $1", message_id)
    await db.execute(
        """
        INSERT INTO audit_log (user_id, method, path, category, status_code, detail)
        VALUES ($1, 'DELETE', $2, 'admin', 200, $3)
        """,
        me_id,
        f"/api/admin/ai/message/{message_id}",
        json.dumps({"deleted_message_id": message_id,
                    "owner_user_id": row["user_id"],
                    "type": row["message_type"]}),
    )
    return {"ok": True, "deleted": message_id}


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
