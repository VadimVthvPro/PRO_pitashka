"""Audit-log middleware: stores every state-changing API call in `audit_log`.

We classify calls by URL prefix into a small set of categories the admin UI
filters on. GET / OPTIONS / HEAD are skipped to keep volume sane (they don't
change state). Static, health, docs and the audit endpoints themselves are
also excluded.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

from fastapi import Request, Response
from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.database import get_pool

logger = logging.getLogger(__name__)

# Order matters — first match wins.
_CATEGORY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ai_food",      re.compile(r"^/api/ai/(food|photo|recognize)")),
    ("ai_workout",   re.compile(r"^/api/ai/workout")),
    ("ai_chat",      re.compile(r"^/api/ai/chat")),
    ("ai_digest",    re.compile(r"^/api/digest/")),
    ("ai_other",     re.compile(r"^/api/ai/")),
    ("food",         re.compile(r"^/api/food/")),
    ("workouts",     re.compile(r"^/api/workouts/")),
    ("water",        re.compile(r"^/api/water/")),
    ("weight",       re.compile(r"^/api/weight/")),
    ("auth",         re.compile(r"^/api/auth/")),
    ("settings",     re.compile(r"^/api/settings/")),
    ("profile",      re.compile(r"^/api/users/")),
    ("social",       re.compile(r"^/api/social/")),
    ("admin",        re.compile(r"^/api/admin/")),
    ("streaks",      re.compile(r"^/api/streaks/")),
    ("summary",      re.compile(r"^/api/summary/")),
]

_SKIP_EXACT = {
    "/api/health",
    "/api/_internal/ai-health",
    "/api/admin/audit",  # don't log fetches of the log itself
}

_SKIP_PREFIXES = (
    "/api/admin/audit",
    "/api/docs",
    "/api/redoc",
    "/openapi",
    "/_next",
    "/static",
)


def _classify(path: str) -> str:
    for cat, rx in _CATEGORY_PATTERNS:
        if rx.match(path):
            return cat
    return "other"


def _user_id_from_request(request: Request) -> Optional[int]:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth[7:]
    if not token:
        return None
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return int(payload.get("sub")) if payload.get("sub") else None
    except Exception:
        return None


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()

        if (
            method in {"GET", "HEAD", "OPTIONS"}
            or path in _SKIP_EXACT
            or any(path.startswith(p) for p in _SKIP_PREFIXES)
            or not path.startswith("/api/")
        ):
            return await call_next(request)

        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        try:
            user_id = _user_id_from_request(request)
            ip = request.client.host if request.client else None
            ua = request.headers.get("user-agent", "")[:500]
            category = _classify(path)
            pool = await get_pool()
            await pool.execute(
                """
                INSERT INTO audit_log
                  (user_id, method, path, category, status_code, duration_ms, ip, user_agent)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                user_id, method, path, category,
                response.status_code, duration_ms, ip, ua,
            )
        except Exception as e:
            # Never fail the request because of logging.
            logger.warning("audit log insert failed: %s", e)

        return response
