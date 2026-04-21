"""Yandex ID (OAuth 2.0 Authorization Code flow).

Flow:
    1. Frontend → GET /api/auth/yandex/authorize?mode=login|link
       → backend строит state (JWT) → 302 на id.yandex.ru с `response_type=code`.
    2. Пользователь даёт разрешения на id.yandex.ru.
    3. Yandex → redirect на /api/auth/yandex/callback?code=...&state=...
    4. Backend:
       a) проверяет state (JWT с purpose+provider=yandex),
       b) POST'ит code на oauth.yandex.ru/token → access_token,
       c) GET login.yandex.ru/info?format=json → профиль,
       d) ищет/создаёт user_main, пишет `yandex_sub`,
       e) ставит сессионные cookies,
       f) 302 на фронт (/dashboard | /onboarding | return_to).

Регистрация приложения: https://oauth.yandex.ru/client/new
Права: `login:info login:email login:avatar`.
Callback URL (ровно этот): {OAUTH_REDIRECT_BASE}/api/auth/yandex/callback
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from app.dependencies import DbDep, SettingsDep, get_current_user_id
from app.services import auth_service
from app.services.auth_cookies import set_auth_cookies
from app.services.oauth_state import sign_oauth_state, verify_oauth_state

logger = logging.getLogger(__name__)
router = APIRouter()

AUTHORIZE_URL = "https://oauth.yandex.ru/authorize"
TOKEN_URL = "https://oauth.yandex.ru/token"
USERINFO_URL = "https://login.yandex.ru/info"

# Минимальный набор scope'ов, нужных для login+email+аватарки.
# Расширять здесь — только если реально нужно (каждый лишний scope
# пугает пользователя на consent-экране).
SCOPES = "login:info login:email login:avatar"


def _redirect_uri(settings) -> str:
    base = (settings.OAUTH_REDIRECT_BASE or settings.FRONTEND_URL or "").rstrip("/")
    return f"{base}/api/auth/yandex/callback"


@router.get("/config")
async def yandex_config(settings: SettingsDep):
    return {"enabled": bool(settings.YANDEX_CLIENT_ID)}


@router.get("/authorize")
async def yandex_authorize(
    settings: SettingsDep,
    request: Request,
    mode: str = Query("login", pattern="^(login|link)$"),
    return_to: str | None = Query(None, max_length=200),
):
    """Стартовая точка flow: редиректим пользователя на consent-экран Яндекса.

    `mode=link` требует, чтобы пользователь уже был залогинен: мы кладём
    его user_id в state и в callback'е привяжем Yandex к нему, а не
    создадим нового.
    """
    if not settings.YANDEX_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Yandex sign-in not configured")

    user_id: int | None = None
    if mode == "link":
        user_id = await get_current_user_id(request, settings)

    state = sign_oauth_state(
        provider="yandex",
        purpose=mode,  # type: ignore[arg-type]
        user_id=user_id,
        return_to=return_to,
    )
    params = {
        "response_type": "code",
        "client_id": settings.YANDEX_CLIENT_ID,
        "redirect_uri": _redirect_uri(settings),
        "scope": SCOPES,
        "state": state,
        # Яндекс не требует force_confirm, но для повторных логинов с
        # другого аккаунта бывает удобно — оставим auto-consent: если
        # пользователь уже давал разрешение, экран просто пропустится.
    }
    return RedirectResponse(f"{AUTHORIZE_URL}?{urlencode(params)}", status_code=302)


async def _exchange_code_for_token(code: str, settings) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.YANDEX_CLIENT_ID,
                "client_secret": settings.YANDEX_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if r.status_code != 200:
        logger.warning("Yandex token exchange failed: %s %s", r.status_code, r.text[:300])
        raise HTTPException(status_code=401, detail="Yandex token exchange failed")
    return r.json()


async def _fetch_profile(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{USERINFO_URL}?format=json",
            headers={"Authorization": f"OAuth {access_token}"},
        )
    if r.status_code != 200:
        logger.warning("Yandex userinfo failed: %s %s", r.status_code, r.text[:300])
        raise HTTPException(status_code=401, detail="Yandex userinfo failed")
    return r.json()


async def _find_or_create_user(db, info: dict[str, Any]) -> tuple[int, bool]:
    sub = str(info["id"])
    email = (info.get("default_email") or "").lower() or None
    login = info.get("login") or None
    display = info.get("display_name") or info.get("real_name") or login
    avatar_id = info.get("default_avatar_id") if not info.get("is_avatar_empty") else None

    row = await db.fetchrow("SELECT user_id FROM user_main WHERE yandex_sub = $1", sub)
    if row:
        return row["user_id"], False

    if email:
        # Если юзер раньше зарегался через Google с тем же email —
        # привязываем Yandex к тому же user_main, чтобы не плодить
        # дубли-аккаунты. VK-matching здесь добавим, когда подключим VK.
        row = await db.fetchrow(
            "SELECT user_id FROM user_main WHERE LOWER(yandex_email) = $1 OR LOWER(google_email) = $1",
            email,
        )
        if row:
            await db.execute(
                """
                UPDATE user_main
                SET yandex_sub = $2,
                    yandex_email = COALESCE($3, yandex_email),
                    yandex_login = COALESCE($4, yandex_login),
                    yandex_avatar_id = COALESCE($5, yandex_avatar_id),
                    yandex_linked_at = COALESCE(yandex_linked_at, NOW())
                WHERE user_id = $1
                """,
                row["user_id"], sub, email, login, avatar_id,
            )
            return row["user_id"], False

    new_id = await auth_service.allocate_synthetic_user_id(db)
    await db.execute(
        """
        INSERT INTO user_main (
            user_id, user_name, display_name,
            yandex_sub, yandex_email, yandex_login, yandex_avatar_id, yandex_linked_at
        )
        VALUES ($1, $2, $2, $3, $4, $5, $6, NOW())
        """,
        new_id, display, sub, email, login, avatar_id,
    )
    return new_id, True


@router.get("/callback")
async def yandex_callback(
    request: Request,
    response: Response,
    db: DbDep,
    settings: SettingsDep,
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
):
    """Обработчик возврата от Яндекса. Всегда 302 на фронт.

    В случае ошибки мы передаём её фронту через query-параметр
    `?auth_error=<msg>` на странице /login, чтобы пользователь увидел
    внятное сообщение и мог повторить попытку.
    """
    frontend = (settings.FRONTEND_URL or "/").rstrip("/")
    login_url = f"{frontend}/login"

    if error:
        logger.info("Yandex callback error: %s %s", error, error_description)
        return RedirectResponse(
            f"{login_url}?auth_error={error}",
            status_code=302,
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="code and state are required")

    try:
        state_payload = verify_oauth_state(state, expected_provider="yandex")
    except ValueError as e:
        logger.warning("Yandex state verification failed: %s", e)
        return RedirectResponse(f"{login_url}?auth_error=bad_state", status_code=302)

    token_data = await _exchange_code_for_token(code, settings)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="No access_token in Yandex response")

    info = await _fetch_profile(access_token)

    purpose = state_payload["purpose"]
    if purpose == "link":
        # Связывание с уже залогиненным пользователем (user_id из state).
        user_id = int(state_payload["uid"])
        sub = str(info["id"])
        email = (info.get("default_email") or "").lower() or None
        other = await db.fetchrow(
            "SELECT user_id FROM user_main WHERE yandex_sub = $1 AND user_id <> $2",
            sub, user_id,
        )
        if other:
            return RedirectResponse(
                f"{frontend}/settings?auth_error=yandex_already_linked",
                status_code=302,
            )
        await db.execute(
            """
            UPDATE user_main
            SET yandex_sub = $2,
                yandex_email = COALESCE($3, yandex_email),
                yandex_login = COALESCE($4, yandex_login),
                yandex_avatar_id = COALESCE($5, yandex_avatar_id),
                yandex_linked_at = NOW()
            WHERE user_id = $1
            """,
            user_id, sub, email,
            info.get("login"),
            info.get("default_avatar_id") if not info.get("is_avatar_empty") else None,
        )
        return RedirectResponse(
            f"{frontend}/settings?auth_linked=yandex",
            status_code=302,
        )

    # purpose == "login"
    user_id, _created = await _find_or_create_user(db, info)

    health = await db.fetchrow(
        "SELECT imt FROM user_health WHERE user_id = $1 ORDER BY date DESC LIMIT 1",
        user_id,
    )
    needs_onboarding = health is None

    access, refresh = await auth_service.create_session(
        db, user_id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    set_auth_cookies(response, settings, access, refresh)

    destination = state_payload.get("rt") or ("/onboarding" if needs_onboarding else "/dashboard")
    if not destination.startswith("/"):
        destination = "/dashboard"
    return RedirectResponse(
        f"{frontend}{destination}",
        status_code=302,
        headers=dict(response.headers),
    )


@router.post("/unlink")
async def yandex_unlink(request: Request, db: DbDep, settings: SettingsDep):
    user_id = await get_current_user_id(request, settings)
    await db.execute(
        """
        UPDATE user_main
        SET yandex_sub = NULL,
            yandex_email = NULL,
            yandex_login = NULL,
            yandex_avatar_id = NULL,
            yandex_linked_at = NULL
        WHERE user_id = $1
        """,
        user_id,
    )
    return {"unlinked": True}
