"""Google Sign-In via Google Identity Services (GIS id_token JWT flow).

Фронт получает ID-токен от Google (через встроенную кнопку GIS или
One Tap) и POST'ит его сюда. Backend проверяет подпись/audience/issuer
по публичным ключам Google (JWKS), извлекает `sub`/`email` и:

1. ищет существующего пользователя по `google_sub`;
2. если не нашёл, пытается привязать по `google_email` к ранее
   зарегистрированной записи (например, пользователь раньше регился
   через Telegram и указывал тот же Gmail);
3. если и это не сработало — создаёт НОВОГО пользователя.

Новая запись получает синтетический user_id из sequence (см. миграцию
016). У неё нет `telegram_username`/`telegram_id` — это фича, а не баг:
у чисто Google-юзера нет Telegram и не должно быть.

Эндпоинты:
    POST /api/auth/google/login  — вход/авторегистрация
    POST /api/auth/google/link   — привязать Google к текущей сессии
    POST /api/auth/google/unlink — отвязать
    GET  /api/auth/google/config — enabled + client_id для фронта
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Body, HTTPException, Request, Response, status
from jose import jwt as jose_jwt
from jose.exceptions import JWTError

from app.dependencies import DbDep, SettingsDep
from app.models.auth import TokenResponse
from app.services import auth_service
from app.services.auth_cookies import set_auth_cookies

logger = logging.getLogger(__name__)
router = APIRouter()

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_certs_cache: dict[str, dict] | None = None


async def _fetch_google_certs() -> dict[str, dict]:
    """Кэшируем Google JWKS на время жизни процесса.

    Ключи ротируются редко (раз в несколько недель); если текущий `kid`
    не найден — сбрасываем кэш и запрашиваем свежий набор.
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
    set_auth_cookies(response, settings, access, refresh)
    return access, refresh


async def _find_or_create_user(db, *, sub: str, email: str, name: str | None, picture: str | None) -> tuple[int, bool]:
    """Найти пользователя по Google-идентификатору или создать нового.

    Возвращает (user_id, created) где created=True, если мы только что
    сделали INSERT. Используется в /login для решения needs_onboarding.

    Стратегия:
    1. Точное совпадение по `google_sub` → уже залогинен через Google → возвращаем.
    2. Совпадение по `google_email` (для ранее зарегистрированных через
       Telegram/Yandex/VK с тем же email) → привязываем Google-sub и
       логиним. Это удобно: пользователь не плодит дубликаты при смене
       провайдера.
    3. Ничего не нашли → создаём новый user_main с синтетическим user_id.
    """
    row = await db.fetchrow(
        "SELECT user_id FROM user_main WHERE google_sub = $1",
        sub,
    )
    if row:
        return row["user_id"], False

    if email:
        row = await db.fetchrow(
            "SELECT user_id FROM user_main WHERE LOWER(google_email) = $1",
            email,
        )
        if row:
            await db.execute(
                """
                UPDATE user_main
                SET google_sub = $2,
                    google_picture = COALESCE($3, google_picture),
                    google_linked_at = COALESCE(google_linked_at, NOW())
                WHERE user_id = $1
                """,
                row["user_id"], sub, picture,
            )
            return row["user_id"], False

    # Авторегистрация: новый синтетический user_id из sequence.
    # display_name и user_name берём из Google-профиля, чтобы в UI
    # сразу было человеческое имя, а не «user 10000000123».
    new_id = await auth_service.allocate_synthetic_user_id(db)
    await db.execute(
        """
        INSERT INTO user_main (
            user_id, user_name, display_name,
            google_sub, google_email, google_picture, google_linked_at
        )
        VALUES ($1, $2, $2, $3, $4, $5, NOW())
        """,
        new_id, name, sub, email or None, picture,
    )
    return new_id, True


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
    """Sign in or sign up with a Google ID token from GIS.

    Если Google-идентичность не распознана — создаём НОВОГО пользователя
    с синтетическим user_id (sequence `user_main_synth_id_seq`).
    Пользователь сразу попадает в `/onboarding`, потому что у него нет
    записи `user_health` и, следовательно, `needs_onboarding=True`.
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

    user_id, _created = await _find_or_create_user(
        db, sub=sub, email=email, name=name, picture=picture,
    )

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
    """Link the current logged-in user to a Google identity."""
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
