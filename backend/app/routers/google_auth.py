"""Google Sign-In via Google Identity Services (GIS).

Frontend uses the GIS button or One Tap to obtain a `credential` (a Google ID
JWT). It POSTs that string here. We verify the signature/audience against
GOOGLE_CLIENT_ID and either:

* link the Google identity to an existing account (current logged-in user),
* recognise a returning user by `sub` and log them in,
* or, if a Telegram account with the same email already exists, link them.

If none of those match — we currently 409 with a hint to register via
Telegram first. We deliberately avoid creating fully unbacked accounts:
PROpitashka still relies on Telegram username for OTP delivery.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Body, HTTPException, Request, Response, status
from jose import jwt as jose_jwt
from jose.exceptions import JWTError

from app.dependencies import DbDep, SettingsDep
from app.models.auth import TokenResponse
from app.services import auth_service

logger = logging.getLogger(__name__)
router = APIRouter()

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_certs_cache: dict[str, dict] | None = None


async def _fetch_google_certs() -> dict[str, dict]:
    """Cache Google's JWK set for the lifetime of the process.

    The JWKS rotates rarely; if a `kid` is missing we'll re-fetch on demand.
    """
    global _certs_cache
    if _certs_cache is not None:
        return _certs_cache
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.get(GOOGLE_CERTS_URL)
        r.raise_for_status()
        data = r.json()
    _certs_cache = {k["kid"]: k for k in data.get("keys", [])}
    return _certs_cache


async def _verify_id_token(id_token: str, audience: str) -> dict:
    """Validate Google ID JWT — issuer, audience, expiry, signature."""
    try:
        header = jose_jwt.get_unverified_header(id_token)
    except JWTError as e:
        raise HTTPException(status_code=400, detail=f"Bad ID token: {e}") from e

    kid = header.get("kid")
    certs = await _fetch_google_certs()
    if kid not in certs:
        # Force refresh in case Google rotated keys.
        global _certs_cache
        _certs_cache = None
        certs = await _fetch_google_certs()
    key = certs.get(kid)
    if not key:
        raise HTTPException(status_code=400, detail="Unknown signing key")

    try:
        payload = jose_jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=audience,
            issuer=("accounts.google.com", "https://accounts.google.com"),
            options={"verify_at_hash": False},
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid ID token: {e}") from e

    if not payload.get("email_verified"):
        raise HTTPException(status_code=403, detail="Google email is not verified")
    return payload


async def _set_session_cookies(
    db, settings, user_id: int, request: Request, response: Response
) -> tuple[str, str]:
    access, refresh = await auth_service.create_session(
        db,
        user_id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    secure = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    return access, refresh


@router.get("/config")
async def google_config(settings: SettingsDep):
    """Tells the frontend whether Google sign-in is available + the client_id."""
    return {
        "enabled": bool(settings.GOOGLE_CLIENT_ID),
        "client_id": settings.GOOGLE_CLIENT_ID,
    }


@router.post("/login", response_model=TokenResponse)
async def google_login(
    request: Request,
    response: Response,
    db: DbDep,
    settings: SettingsDep,
    body: dict = Body(...),
):
    """Sign in (or sign up) with a Google ID token from GIS.

    Lookup order:
      1. user_main.google_sub == sub  → existing Google user.
      2. user_main.google_email == email (case-insensitive) → relink stale row.
      3. — no auto-create yet — return 409 so the frontend can prompt the
        user to finish Telegram registration first.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in not configured")

    credential = (body.get("credential") or "").strip()
    if not credential:
        raise HTTPException(status_code=400, detail="credential is required")

    payload = await _verify_id_token(credential, audience=settings.GOOGLE_CLIENT_ID)
    sub: str = payload["sub"]
    email: str = (payload.get("email") or "").lower()
    name: str | None = payload.get("name")
    picture: str | None = payload.get("picture")

    user = await db.fetchrow(
        "SELECT user_id FROM user_main WHERE google_sub = $1",
        sub,
    )
    if not user and email:
        user = await db.fetchrow(
            "SELECT user_id, google_sub FROM user_main WHERE LOWER(google_email) = $1",
            email,
        )
        if user:
            await db.execute(
                """
                UPDATE user_main
                SET google_sub = $2, google_picture = COALESCE($3, google_picture),
                    google_linked_at = COALESCE(google_linked_at, NOW())
                WHERE user_id = $1
                """,
                user["user_id"], sub, picture,
            )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "google_account_not_linked",
                "message": (
                    "У этого Google-аккаунта нет привязки. "
                    "Зайди через Telegram и нажми «Привязать Google» в Настройках."
                ),
                "email": email,
            },
        )

    user_id = user["user_id"]

    health = await db.fetchrow(
        "SELECT imt FROM user_health WHERE user_id = $1 ORDER BY date DESC LIMIT 1",
        user_id,
    )
    needs_onboarding = health is None

    access, _ = await _set_session_cookies(db, settings, user_id, request, response)
    return TokenResponse(
        access_token=access,
        user_id=user_id,
        needs_onboarding=needs_onboarding,
    )


@router.post("/link")
async def google_link(
    request: Request,
    db: DbDep,
    settings: SettingsDep,
    body: dict = Body(...),
):
    """Link the current logged-in Telegram user to a Google identity."""
    from app.dependencies import get_current_user_id

    user_id = await get_current_user_id(request, settings)
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in not configured")

    credential = (body.get("credential") or "").strip()
    if not credential:
        raise HTTPException(status_code=400, detail="credential is required")

    payload = await _verify_id_token(credential, audience=settings.GOOGLE_CLIENT_ID)
    sub: str = payload["sub"]
    email: str = (payload.get("email") or "").lower()
    picture: str | None = payload.get("picture")

    other = await db.fetchrow(
        "SELECT user_id FROM user_main WHERE google_sub = $1 AND user_id <> $2",
        sub, user_id,
    )
    if other:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Этот Google-аккаунт уже привязан к другому пользователю",
        )

    await db.execute(
        """
        UPDATE user_main
        SET google_sub = $2,
            google_email = COALESCE($3, google_email),
            google_picture = COALESCE($4, google_picture),
            google_linked_at = NOW()
        WHERE user_id = $1
        """,
        user_id, sub, email, picture,
    )
    return {"linked": True, "email": email}


@router.post("/unlink")
async def google_unlink(request: Request, db: DbDep, settings: SettingsDep):
    from app.dependencies import get_current_user_id

    user_id = await get_current_user_id(request, settings)
    await db.execute(
        """
        UPDATE user_main
        SET google_sub = NULL,
            google_picture = NULL,
            google_linked_at = NULL
        WHERE user_id = $1
        """,
        user_id,
    )
    return {"unlinked": True}
