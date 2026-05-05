import hashlib
import hmac
import json
import secrets
from typing import Any, Optional

from fastapi import APIRouter, Body, Cookie, HTTPException, Query, Request, Response
from app.config import get_settings
from app.dependencies import DbDep, CurrentUserDep, RedisDep
from app.repositories.admin_repo import AdminRepository
from app.repositories.billing_repo import BillingRepository
from app.services import subscription_service

router = APIRouter()

ALLOWED_TABLES = {
    "user_main", "user_lang", "user_health", "user_aims",
    "food", "water", "user_training", "training_types",
    "training_coefficients", "chat_history", "admin_users",
    "web_sessions", "otp_codes", "user_settings",
    "audit_log", "social_posts", "social_likes", "social_follows",
    "app_settings",
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

    try:
        await db.execute("SET LOCAL statement_timeout = '15s'")
        deleted = await repo.delete_row(table_name, pk_column, typed_value)
    except Exception as exc:
        msg = getattr(exc, "detail", None) or str(exc) or exc.__class__.__name__
        raise HTTPException(status_code=400, detail=f"DB rejected delete: {msg[:300]}")
    if not deleted:
        raise HTTPException(status_code=404, detail="Row not found")

    await db.execute(
        """
        INSERT INTO audit_log (user_id, method, path, category, status_code, duration_ms, detail)
        VALUES ($1, 'DELETE', $2, 'admin', 200, 0, $3)
        """,
        user_id,
        f"/api/admin/tables/{table_name}/{pk_column}/{pk_value}",
        json.dumps({"table": table_name, "pk_column": pk_column, "pk_value": str(pk_value)}),
    )
    return {"message": "Deleted"}


# ---------------------------------------------------------------------------
# Row-level editor for the "Tables" panel.
#
# Every real write goes through a hard-coded whitelist (see
# ``app.services.table_policy``) so that the generic /tables endpoint can
# never be used to self-promote an admin, rewrite chat_history, or bypass
# moderation endpoints like /users/{id}/ban.
# ---------------------------------------------------------------------------


def _cast_cell_value(raw: Any, col_meta: dict) -> Any:
    """Coerce incoming JSON value to the column's Postgres type.

    We trust ``col_meta`` from ``information_schema`` to decide the target
    type; the whitelist in ``table_policy`` is what protects *which*
    columns can be written at all.

    IMPORTANT: asyncpg is strictly typed — it will NOT accept ISO strings
    for ``date`` / ``time`` / ``timestamp`` columns. We parse strings into
    native Python objects on this side; passing them through raw would
    surface as a 500 (asyncpg DataError) instead of a clean 400.
    """
    import datetime as _dt

    dtype = (col_meta.get("data_type") or "").lower()
    nullable = (col_meta.get("is_nullable") or "NO").upper() == "YES"
    col_name = col_meta.get("column_name", "?")

    # Explicit NULL
    if raw is None or raw == "":
        if nullable:
            return None
        if dtype in ("text", "character varying", "varchar", "character", "char"):
            return ""
        raise HTTPException(
            status_code=400,
            detail=f"column {col_name} is NOT NULL",
        )

    if dtype == "boolean":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            if raw.lower() in ("true", "t", "1", "yes", "y"):
                return True
            if raw.lower() in ("false", "f", "0", "no", "n"):
                return False
        if isinstance(raw, (int, float)):
            return bool(raw)
        raise HTTPException(status_code=400, detail=f"invalid boolean value for {col_name}")

    if dtype in ("integer", "bigint", "smallint"):
        try:
            return int(raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"invalid integer value for {col_name}")

    if dtype in ("numeric", "real", "double precision"):
        try:
            return float(raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"invalid numeric value for {col_name}")

    if dtype in ("json", "jsonb"):
        if isinstance(raw, (dict, list)):
            return json.dumps(raw)
        if isinstance(raw, str):
            try:
                json.loads(raw)
            except Exception:
                raise HTTPException(status_code=400, detail=f"invalid JSON value for {col_name}")
            return raw
        raise HTTPException(status_code=400, detail=f"invalid JSON value for {col_name}")

    # --- date / time / timestamp ------------------------------------------
    # asyncpg wants native datetime objects here, not ISO strings.
    if dtype == "date":
        if isinstance(raw, _dt.date) and not isinstance(raw, _dt.datetime):
            return raw
        if isinstance(raw, str):
            try:
                return _dt.date.fromisoformat(raw[:10])
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"invalid date for {col_name} — expected YYYY-MM-DD",
                )
        raise HTTPException(status_code=400, detail=f"invalid date for {col_name}")

    if dtype in ("time", "time without time zone", "time with time zone"):
        if isinstance(raw, _dt.time):
            return raw
        if isinstance(raw, str):
            try:
                # Accept HH:MM or HH:MM:SS or HH:MM:SS.ffffff
                return _dt.time.fromisoformat(raw)
            except ValueError:
                try:
                    # One more retry: "HH:MM" only
                    parts = [int(p) for p in raw.split(":")]
                    return _dt.time(*(parts + [0] * (3 - len(parts)))[:3])
                except Exception:
                    raise HTTPException(
                        status_code=400,
                        detail=f"invalid time for {col_name} — expected HH:MM[:SS]",
                    )
        raise HTTPException(status_code=400, detail=f"invalid time for {col_name}")

    if dtype in ("timestamp", "timestamp without time zone",
                 "timestamp with time zone", "timestamptz"):
        if isinstance(raw, _dt.datetime):
            return raw
        if isinstance(raw, str):
            # Accept "YYYY-MM-DD", "YYYY-MM-DDTHH:MM[:SS][Z|+HH:MM]"
            s = raw.strip()
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            try:
                return _dt.datetime.fromisoformat(s)
            except ValueError:
                try:
                    # Date-only → midnight
                    return _dt.datetime.combine(
                        _dt.date.fromisoformat(s[:10]), _dt.time(0, 0)
                    )
                except Exception:
                    raise HTTPException(
                        status_code=400,
                        detail=f"invalid timestamp for {col_name} — expected ISO-8601",
                    )
        raise HTTPException(status_code=400, detail=f"invalid timestamp for {col_name}")

    # Fallback: treat as text
    return str(raw)


def _parse_pk(pk_value: str) -> int | str:
    try:
        return int(pk_value)
    except (TypeError, ValueError):
        return pk_value


def _json_safe(value: Any) -> Any:
    """Render datetimes / Decimal / bytes for JSON output."""
    import datetime as _dt
    import decimal as _dec

    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat()
    if isinstance(value, _dec.Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return repr(value)
    return value


@router.get("/tables/{table_name}/{pk_column}/{pk_value}")
async def get_single_row(
    table_name: str, pk_column: str, pk_value: str,
    request: Request, db: DbDep,
):
    """One row + the policy describing which of its columns are editable."""
    from app.services import table_policy as _tp

    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)

    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail="Table not found")

    repo = AdminRepository(db)
    columns = await repo.get_table_columns(table_name)
    valid_columns = {c["column_name"] for c in columns}
    if pk_column not in valid_columns:
        raise HTTPException(status_code=400, detail=f"Invalid column: {pk_column}")

    policy = _tp.policy_for(table_name) or {}
    try:
        row = await repo.get_row(table_name, pk_column, _parse_pk(pk_value))
    except Exception as exc:
        msg = getattr(exc, "detail", None) or str(exc) or exc.__class__.__name__
        raise HTTPException(status_code=400, detail=f"DB rejected lookup: {msg[:300]}")
    if row is None:
        raise HTTPException(status_code=404, detail="Row not found")

    row_safe = {k: _json_safe(v) for k, v in row.items()}
    return {
        "columns": columns,
        "row": row_safe,
        "policy": {
            "pk": policy.get("pk"),
            "editable": sorted(_tp.editable_columns(table_name)),
            "read_only": _tp.is_read_only(table_name),
            "hint_key": policy.get("hint_key"),
        },
    }


@router.patch("/tables/{table_name}/{pk_column}/{pk_value}")
async def update_table_row(
    table_name: str, pk_column: str, pk_value: str,
    request: Request, db: DbDep,
    body: dict = Body(...),
):
    """Update a whitelisted subset of columns in a single row.

    ``body`` is a flat ``{column: new_value}``. Any column absent from the
    table's policy (or in ``GLOBAL_FORBIDDEN_COLS``) is rejected with 400
    — this is what makes the editor safe to expose. The whole update runs
    in a single UPDATE and writes a diff to ``audit_log``.
    """
    from app.services import table_policy as _tp

    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)

    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail="Table not found")
    if _tp.is_read_only(table_name):
        raise HTTPException(status_code=403, detail="table is read-only")

    allowed = _tp.editable_columns(table_name)
    if not allowed:
        raise HTTPException(status_code=403, detail="table has no editable columns")

    if not isinstance(body, dict) or not body:
        raise HTTPException(status_code=400, detail="empty body")

    repo = AdminRepository(db)
    columns = await repo.get_table_columns(table_name)
    col_by_name = {c["column_name"]: c for c in columns}

    if pk_column not in col_by_name:
        raise HTTPException(status_code=400, detail=f"Invalid column: {pk_column}")

    # --- validate & cast --------------------------------------------------
    set_map: dict[str, Any] = {}
    for col, raw in body.items():
        if col not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"column '{col}' is not editable",
            )
        meta = col_by_name.get(col)
        if not meta:
            raise HTTPException(
                status_code=400,
                detail=f"unknown column: {col}",
            )
        set_map[col] = _cast_cell_value(raw, meta)

    pk_typed = _parse_pk(pk_value)

    # --- read current row for audit diff ---------------------------------
    try:
        before = await repo.get_row(table_name, pk_column, pk_typed)
    except Exception as exc:
        msg = getattr(exc, "detail", None) or str(exc) or exc.__class__.__name__
        raise HTTPException(status_code=400, detail=f"DB rejected lookup: {msg[:300]}")
    if before is None:
        raise HTTPException(status_code=404, detail="Row not found")

    # Drop no-op changes (saves audit spam).
    changes: dict[str, Any] = {}
    for col, new in set_map.items():
        old = before.get(col)
        if old != new:
            changes[col] = new
    if not changes:
        return {"ok": True, "changed": [], "row": {k: _json_safe(v) for k, v in before.items()}}

    try:
        await db.execute("SET LOCAL statement_timeout = '15s'")
        updated = await repo.update_row(table_name, pk_column, pk_typed, changes)
    except Exception as exc:  # asyncpg.PostgresError + DataError land here
        msg = getattr(exc, "detail", None) or str(exc) or exc.__class__.__name__
        raise HTTPException(status_code=400, detail=f"DB rejected update: {msg[:300]}")
    if updated is None:
        raise HTTPException(status_code=404, detail="Row not found")

    # --- audit -----------------------------------------------------------
    diff = {}
    for col in changes.keys():
        b = before.get(col)
        a = updated.get(col)
        # Truncate long strings so the audit_log doesn't bloat
        if isinstance(b, str) and len(b) > 200:
            b = b[:200] + "…"
        if isinstance(a, str) and len(a) > 200:
            a = a[:200] + "…"
        diff[col] = {"before": _json_safe(b), "after": _json_safe(a)}

    await db.execute(
        """
        INSERT INTO audit_log (user_id, method, path, category, status_code, duration_ms, detail)
        VALUES ($1, 'PATCH', $2, 'admin', 200, 0, $3)
        """,
        me_id,
        f"/api/admin/tables/{table_name}/{pk_column}/{pk_value}",
        json.dumps({
            "table": table_name,
            "pk_column": pk_column,
            "pk_value": str(pk_value),
            "diff": diff,
        }),
    )

    return {
        "ok": True,
        "changed": list(changes.keys()),
        "row": {k: _json_safe(v) for k, v in updated.items()},
    }


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
        INSERT INTO audit_log (user_id, method, path, category, status_code, duration_ms, detail)
        VALUES ($1, 'DELETE', $2, 'admin', 200, 0, $3)
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


# ---------------------------------------------------------------------------
# User editing — name, goal, daily_cal, tier, ban, feature toggles.
# Only a safe subset of columns is editable; everything else is read-only.
# ---------------------------------------------------------------------------

EDITABLE_USER_FIELDS = {
    # user_main
    "user_name":        {"type": "string", "max_len": 255},
    "display_name":     {"type": "string", "max_len": 64},
    "bio":              {"type": "string", "max_len": 280, "nullable": True},
    "user_sex":         {"type": "enum",   "values": ("m", "f", "M", "F", "")},
    "gender":           {"type": "string", "max_len": 16, "nullable": True},
    "public_profile":   {"type": "bool"},
    "tier":             {"type": "enum",   "values": ("free", "pro", "elite", "admin")},
    "ai_disabled":      {"type": "bool"},
    "social_disabled":  {"type": "bool"},
    "is_premium":       {"type": "bool"},
    "social_score":     {"type": "int"},
}


def _coerce_user_value(field: str, raw: Any) -> Any:
    spec = EDITABLE_USER_FIELDS[field]
    if raw is None:
        if spec.get("nullable") or spec["type"] == "string":
            return None
        raise HTTPException(status_code=400, detail=f"{field} must not be null")
    t = spec["type"]
    if t == "bool":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return bool(raw)
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on"}
        raise HTTPException(status_code=400, detail=f"{field} must be boolean")
    if t == "int":
        try:
            return int(raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"{field} must be integer")
    if t == "enum":
        if str(raw) not in spec["values"]:
            raise HTTPException(
                status_code=400,
                detail=f"{field} must be one of {list(spec['values'])}",
            )
        return str(raw)
    # string
    s = "" if raw is None else str(raw)
    if len(s) > spec.get("max_len", 255):
        raise HTTPException(
            status_code=400,
            detail=f"{field}: max {spec.get('max_len', 255)} chars",
        )
    return s or None if spec.get("nullable") else s


@router.patch("/users/{target_id}")
async def admin_user_patch(
    target_id: int,
    request: Request,
    db: DbDep,
    body: dict = Body(...),
):
    """Update a safe subset of user columns.

    Accepts a flat dict ``{field: value}``. Unknown fields are rejected. The
    whole update runs in a single UPDATE statement so partial failures are
    impossible. Every call logs to ``audit_log`` with the set of changed
    fields (values are recorded for scalar fields only — booleans/ints are
    cheap to store, bio/display_name are truncated to avoid audit bloat).
    """
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)

    if not body:
        raise HTTPException(status_code=400, detail="empty body")

    existing = await db.fetchrow("SELECT user_id FROM user_main WHERE user_id = $1", target_id)
    if not existing:
        raise HTTPException(status_code=404, detail="user not found")

    updates: dict[str, Any] = {}
    for field, raw in body.items():
        if field not in EDITABLE_USER_FIELDS:
            raise HTTPException(status_code=400, detail=f"unknown field: {field}")
        updates[field] = _coerce_user_value(field, raw)

    set_clauses = [f"{col} = ${idx}" for idx, col in enumerate(updates.keys(), start=1)]
    values = list(updates.values())
    values.append(target_id)
    try:
        await db.execute("SET LOCAL statement_timeout = '15s'")
        await db.execute(
            f"UPDATE user_main SET {', '.join(set_clauses)} WHERE user_id = ${len(values)}",
            *values,
        )
    except Exception as exc:
        msg = getattr(exc, "detail", None) or str(exc) or exc.__class__.__name__
        raise HTTPException(status_code=400, detail=f"DB rejected update: {msg[:300]}")

    # Audit: keep large strings out of JSONB — truncate bio/display_name.
    audit_payload = {k: (v[:120] + "…") if isinstance(v, str) and len(v) > 120 else v
                     for k, v in updates.items()}
    await db.execute(
        """
        INSERT INTO audit_log (user_id, method, path, category, status_code, duration_ms, detail)
        VALUES ($1, 'PATCH', $2, 'admin', 200, 0, $3)
        """,
        me_id,
        f"/api/admin/users/{target_id}",
        json.dumps({"target": target_id, "changes": audit_payload}),
    )
    return {"ok": True, "changed": list(updates.keys())}


@router.post("/users/{target_id}/ban")
async def admin_user_ban(
    target_id: int,
    request: Request,
    db: DbDep,
    body: dict = Body(default={}),
):
    """Mark user as banned — sets ``banned_at = NOW()`` and records reason."""
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)
    reason = (body or {}).get("reason") or None
    if reason is not None and len(reason) > 280:
        reason = reason[:280]
    row = await db.fetchrow(
        """
        UPDATE user_main
        SET banned_at = NOW(), ban_reason = $2
        WHERE user_id = $1
        RETURNING user_id, banned_at
        """,
        target_id, reason,
    )
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    await db.execute(
        """
        INSERT INTO audit_log (user_id, method, path, category, status_code, duration_ms, detail)
        VALUES ($1, 'POST', $2, 'admin', 200, 0, $3)
        """,
        me_id, f"/api/admin/users/{target_id}/ban",
        json.dumps({"target": target_id, "reason": reason}),
    )
    return {"ok": True, "banned_at": row["banned_at"].isoformat()}


@router.post("/users/{target_id}/unban")
async def admin_user_unban(target_id: int, request: Request, db: DbDep):
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)
    row = await db.fetchrow(
        """
        UPDATE user_main
        SET banned_at = NULL, ban_reason = NULL
        WHERE user_id = $1
        RETURNING user_id
        """,
        target_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    await db.execute(
        """
        INSERT INTO audit_log (user_id, method, path, category, status_code, duration_ms, detail)
        VALUES ($1, 'POST', $2, 'admin', 200, 0, $3)
        """,
        me_id, f"/api/admin/users/{target_id}/unban",
        json.dumps({"target": target_id}),
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Subscription management — выдача / отзыв тира из админки.
# Не использует Stars-инвойсы — даёт подписку напрямую через
# subscription_service.grant() с source='admin'.
# ---------------------------------------------------------------------------


@router.post("/users/{target_id}/grant-tier")
async def admin_grant_tier(
    target_id: int,
    request: Request,
    db: DbDep,
    redis: RedisDep,
    body: dict = Body(...),
):
    """Выдаёт юзеру платный тир в обход оплаты.

    Body:
        ``{"plan_key": "premium_month", "days": 30}``  — оба опциональны.
        - ``plan_key`` дефолт ``premium_month`` (берётся из tier_plans).
        - ``days``     если задан — переопределяет ``duration_days`` плана
                       (можно выдать пробный 7-дневный premium).

    Идемпотентен: повторный вызов продлевает существующую активную
    подписку того же tier (см. subscription_service.grant). Списание
    происходит через `source='admin'`, без записи в `star_payments`.
    """
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)

    if not await db.fetchrow("SELECT user_id FROM user_main WHERE user_id = $1", target_id):
        raise HTTPException(status_code=404, detail="user not found")

    plan_key = (body or {}).get("plan_key") or "premium_month"
    raw_days = (body or {}).get("days")

    repo = BillingRepository(db)
    plan = await repo.get_plan(plan_key)
    if not plan or plan.get("tier") == "free":
        raise HTTPException(
            status_code=400,
            detail=f"plan_key {plan_key!r} not found or is free",
        )

    # Опциональное переопределение длительности — для пробных периодов.
    if raw_days is not None:
        try:
            days_int = int(raw_days)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="days must be integer")
        if days_int <= 0 or days_int > 3650:
            raise HTTPException(status_code=400, detail="days must be in 1..3650")
        # Подмена duration_days на лету — БЕЗ записи в tier_plans.
        # subscription_service.grant читает duration_days из get_plan() →
        # делаем тонкую обёртку, временно подсовывая нужное число.
        async def _shim_get_plan(_pk: str):  # noqa: ANN001
            row = await repo.get_plan(_pk)
            if row and _pk == plan_key:
                row = dict(row)
                row["duration_days"] = days_int
            return row

        # monkey-patch на уровне репозитория НЕ делаем — duplicateriy.
        # Вместо этого вычислим end_at сами и пойдём чуть-чуть в обход
        # subscription_service.grant: используем admin_grant_custom_days.
        result = await _grant_custom_days(
            db, redis,
            user_id=target_id, plan_key=plan_key, days=days_int,
            source="admin",
        )
    else:
        try:
            result = await subscription_service.grant(
                db, redis,
                user_id=target_id,
                plan_key=plan_key,
                source="admin",
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    await db.execute(
        """
        INSERT INTO audit_log (user_id, method, path, category, status_code, duration_ms, detail)
        VALUES ($1, 'POST', $2, 'admin', 200, 0, $3)
        """,
        me_id, f"/api/admin/users/{target_id}/grant-tier",
        json.dumps({
            "target": target_id, "plan_key": plan_key,
            "days_override": raw_days,
        }),
    )

    return {
        "ok": True,
        "tier": result.get("tier"),
        "plan_key": result.get("plan_key"),
        "end_at": result["end_at"].isoformat() if result.get("end_at") else None,
        "source": result.get("source"),
    }


async def _grant_custom_days(
    db, redis, *,
    user_id: int, plan_key: str, days: int, source: str,
):
    """Вариант subscription_service.grant с явным числом дней.

    Нужен для админ-выдачи на нестандартный срок (триал на 7 дней
    при базовом duration_days=30, или подарок на год). Логика 1-в-1 как
    в основном grant(), но `duration_days` берётся из аргумента.
    """
    from datetime import datetime, timedelta, timezone

    repo = BillingRepository(db)
    plan = await repo.get_plan(plan_key)
    if not plan or plan.get("tier") == "free":
        raise HTTPException(status_code=400, detail=f"plan {plan_key!r} not grantable")

    now = datetime.now(timezone.utc)
    existing = await repo.get_active_subscription(user_id)
    start_at = (
        existing["end_at"]
        if existing and existing["tier"] == plan["tier"] and existing["end_at"] > now
        else now
    )
    end_at = start_at + timedelta(days=days)

    async with db.acquire() as conn:
        async with conn.transaction():
            await repo.expire_active_subscriptions(conn, user_id)
            await repo.insert_subscription(
                conn,
                user_id=user_id, plan_key=plan_key,
                tier=plan["tier"], status="active",
                source=source, start_at=start_at, end_at=end_at,
                payment_id=None,
            )
            await conn.execute(
                """
                UPDATE user_main
                   SET is_premium = TRUE, premium_until = $2
                 WHERE user_id = $1
                """,
                user_id, end_at.replace(tzinfo=None),
            )

    # Сбрасываем кеш subscription_service, иначе resolve() ещё минуту
    # будет отдавать старый тир.
    if redis is not None:
        try:
            await redis.delete(f"sub:{user_id}")
        except Exception:
            pass

    return await subscription_service.resolve(db, redis, user_id)


@router.post("/users/{target_id}/revoke-tier")
async def admin_revoke_tier(
    target_id: int, request: Request, db: DbDep, redis: RedisDep,
):
    """Жёстко закрывает все активные подписки юзера (downgrade на free)."""
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)
    if not await db.fetchrow("SELECT user_id FROM user_main WHERE user_id = $1", target_id):
        raise HTTPException(status_code=404, detail="user not found")
    await subscription_service.admin_expire_all(db, redis, target_id)
    await db.execute(
        """
        INSERT INTO audit_log (user_id, method, path, category, status_code, duration_ms, detail)
        VALUES ($1, 'POST', $2, 'admin', 200, 0, $3)
        """,
        me_id, f"/api/admin/users/{target_id}/revoke-tier",
        json.dumps({"target": target_id}),
    )
    return {"ok": True, "tier": "free"}


@router.get("/users/{target_id}/subscriptions")
async def admin_user_subscriptions(target_id: int, request: Request, db: DbDep, redis: RedisDep):
    """Текущая активная подписка + история (последние 20)."""
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)
    repo = BillingRepository(db)
    current = await subscription_service.resolve(db, redis, target_id)
    history = await repo.list_subscriptions(target_id, limit=20)
    return {
        "current": {
            "tier": current.get("tier"),
            "plan_key": current.get("plan_key"),
            "end_at": current["end_at"].isoformat() if current.get("end_at") else None,
            "source": current.get("source"),
            "name": current.get("name") or current.get("plan_key"),
        },
        "history": [
            {
                **{k: v for k, v in row.items() if not isinstance(v, (bytes, bytearray))},
                "start_at": row["start_at"].isoformat() if row.get("start_at") else None,
                "end_at": row["end_at"].isoformat() if row.get("end_at") else None,
                "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            }
            for row in history
        ],
    }


# ---------------------------------------------------------------------------
# Runtime settings (app_settings) — AI model/timeouts, free-tier limits, flags
# ---------------------------------------------------------------------------


@router.get("/settings")
async def admin_list_settings(request: Request, db: DbDep):
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)
    from app.services.runtime_settings import list_settings
    return {"items": await list_settings()}


@router.put("/settings/{key}")
async def admin_set_setting(
    key: str, request: Request, db: DbDep, body: dict = Body(...),
):
    """Update a single runtime setting.

    Body: ``{"value": ...}``. The value is coerced to the declared type in
    ``runtime_settings.KNOWN_SETTINGS``. Writes are audited.
    """
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)
    from app.services.runtime_settings import KNOWN_SETTINGS, set_setting
    if key not in KNOWN_SETTINGS:
        raise HTTPException(status_code=400, detail=f"unknown setting: {key}")
    if "value" not in (body or {}):
        raise HTTPException(status_code=400, detail="missing 'value'")
    try:
        stored = await set_setting(key, body["value"], updated_by=me_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.execute(
        """
        INSERT INTO audit_log (user_id, method, path, category, status_code, duration_ms, detail)
        VALUES ($1, 'PUT', $2, 'admin', 200, 0, $3)
        """,
        me_id, f"/api/admin/settings/{key}",
        json.dumps({"key": key, "new_value": stored}),
    )
    return {"ok": True, "key": key, "value": stored}


@router.get("/env-view")
async def admin_env_view(request: Request, db: DbDep):
    """Metadata-only view of secret-carrying env vars.

    Never returns raw values. For each known secret we return
    ``{present, length, prefix, tail}`` so the admin can confirm the right
    key is loaded without reading it back.
    """
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)
    from app.services import ai_service as _ai
    settings = get_settings()

    def mask(v: str | None, show_prefix: int = 4, show_tail: int = 4) -> dict:
        if not v:
            return {"present": False, "length": 0, "prefix": None, "tail": None}
        v = str(v)
        return {
            "present": True,
            "length": len(v),
            "prefix": v[:show_prefix] + "…" if len(v) > show_prefix else v,
            "tail": "…" + v[-show_tail:] if len(v) > show_tail else v,
        }

    return {
        "environment": settings.ENVIRONMENT,
        "secrets": {
            "GEMINI_API_KEY":     mask(settings.GEMINI_API_KEY, 6, 4),
            "JWT_SECRET_KEY":     mask(settings.JWT_SECRET_KEY, 4, 4),
            "ADMIN_PASSWORD":     mask(settings.ADMIN_PASSWORD, 2, 2),
            "DB_PASSWORD":        mask(settings.DB_PASSWORD, 2, 2),
            "TELEGRAM_TOKEN":     mask(settings.TELEGRAM_TOKEN, 6, 4),
            "GOOGLE_CLIENT_ID":   mask(settings.GOOGLE_CLIENT_ID, 12, 6),
        },
        "ai_model_effective": _ai._current_model_name(),  # noqa: SLF001
        "ai_model_env":       settings.GEMINI_MODEL,
        "frontend_url":       settings.FRONTEND_URL,
    }


# ---------------------------------------------------------------------------
# Social moderation — posts list with hidden/pinned state, mutation endpoints
# ---------------------------------------------------------------------------


@router.get("/social/posts")
async def admin_social_posts(
    request: Request,
    db: DbDep,
    search: Optional[str] = Query(None, description="Substring of title/body/tags"),
    status: str = Query("all", pattern=r"^(all|visible|hidden|pinned)$"),
    kind: Optional[str] = Query(None, pattern=r"^(form|meal|workout)$"),
    target_user: Optional[int] = Query(None, alias="user_id"),
    limit: int = Query(40, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)

    where = ["1=1"]
    args: list[Any] = []
    if status == "visible":
        where.append("sp.hidden_at IS NULL")
    elif status == "hidden":
        where.append("sp.hidden_at IS NOT NULL")
    elif status == "pinned":
        where.append("sp.pinned_at IS NOT NULL")
    if kind:
        args.append(kind)
        where.append(f"sp.kind = ${len(args)}")
    if target_user is not None:
        args.append(target_user)
        where.append(f"sp.user_id = ${len(args)}")
    if search:
        args.append(f"%{search.lower()}%")
        where.append(
            f"(LOWER(COALESCE(sp.title,'')) LIKE ${len(args)} "
            f" OR LOWER(sp.body) LIKE ${len(args)} "
            f" OR EXISTS (SELECT 1 FROM unnest(sp.tags) t WHERE LOWER(t) LIKE ${len(args)}))"
        )

    args_with_paging = [*args, limit, offset]
    rows = await db.fetch(
        f"""
        SELECT sp.id, sp.user_id, sp.kind, sp.title, sp.body, sp.tags,
               sp.likes_count, sp.created_at, sp.hidden_at, sp.hidden_reason,
               sp.pinned_at,
               COALESCE(um.display_name, um.user_name, um.telegram_username, 'user') AS author_name,
               um.telegram_username
        FROM social_posts sp
        LEFT JOIN user_main um ON um.user_id = sp.user_id
        WHERE {' AND '.join(where)}
        ORDER BY (sp.pinned_at IS NOT NULL) DESC,
                 COALESCE(sp.pinned_at, sp.created_at) DESC
        LIMIT ${len(args_with_paging) - 1} OFFSET ${len(args_with_paging)}
        """,
        *args_with_paging,
    )
    total = await db.fetchval(
        f"SELECT COUNT(*) FROM social_posts sp WHERE {' AND '.join(where)}",
        *args,
    )
    return {
        "items": [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "author_name": r["author_name"],
                "telegram_username": r["telegram_username"],
                "kind": r["kind"],
                "title": r["title"],
                "body": r["body"],
                "tags": list(r["tags"] or []),
                "likes_count": int(r["likes_count"] or 0),
                "created_at": r["created_at"].isoformat(),
                "hidden_at": r["hidden_at"].isoformat() if r["hidden_at"] else None,
                "hidden_reason": r["hidden_reason"],
                "pinned_at": r["pinned_at"].isoformat() if r["pinned_at"] else None,
            }
            for r in rows
        ],
        "total": int(total or 0),
    }


@router.patch("/social/posts/{post_id}")
async def admin_social_post_patch(
    post_id: int,
    request: Request,
    db: DbDep,
    body: dict = Body(...),
):
    """Apply one of: ``{action: "hide" | "unhide" | "pin" | "unpin"}``.

    Optional ``reason`` (max 280 chars) is stored for hide only.
    """
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)
    action = (body or {}).get("action")
    reason = (body or {}).get("reason") or None
    if action not in {"hide", "unhide", "pin", "unpin"}:
        raise HTTPException(status_code=400, detail="action must be hide|unhide|pin|unpin")
    if reason and len(reason) > 280:
        reason = reason[:280]

    exists = await db.fetchval("SELECT 1 FROM social_posts WHERE id = $1", post_id)
    if not exists:
        raise HTTPException(status_code=404, detail="post not found")

    if action == "hide":
        await db.execute(
            "UPDATE social_posts SET hidden_at = NOW(), hidden_reason = $2 WHERE id = $1",
            post_id, reason,
        )
    elif action == "unhide":
        await db.execute(
            "UPDATE social_posts SET hidden_at = NULL, hidden_reason = NULL WHERE id = $1",
            post_id,
        )
    elif action == "pin":
        await db.execute(
            "UPDATE social_posts SET pinned_at = NOW() WHERE id = $1", post_id,
        )
    else:  # unpin
        await db.execute(
            "UPDATE social_posts SET pinned_at = NULL WHERE id = $1", post_id,
        )

    await db.execute(
        """
        INSERT INTO audit_log (user_id, method, path, category, status_code, duration_ms, detail)
        VALUES ($1, 'PATCH', $2, 'social', 200, 0, $3)
        """,
        me_id, f"/api/admin/social/posts/{post_id}",
        json.dumps({"post_id": post_id, "action": action, "reason": reason}),
    )
    return {"ok": True, "action": action}


@router.delete("/social/posts/{post_id}")
async def admin_social_post_delete(post_id: int, request: Request, db: DbDep):
    me_id = await _try_user_id(request)
    await _admin_or_password(request, me_id, db)
    row = await db.fetchrow(
        "SELECT user_id FROM social_posts WHERE id = $1", post_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="post not found")
    await db.execute("DELETE FROM social_posts WHERE id = $1", post_id)
    await db.execute(
        """
        INSERT INTO audit_log (user_id, method, path, category, status_code, duration_ms, detail)
        VALUES ($1, 'DELETE', $2, 'social', 200, 0, $3)
        """,
        me_id, f"/api/admin/social/posts/{post_id}",
        json.dumps({"post_id": post_id, "owner_user_id": row["user_id"]}),
    )
    return {"ok": True, "deleted": post_id}
