"""Auth endpoints: Telegram OTP verification, magic link, refresh, logout.

Два способа войти через Telegram OTP:

1. **Ручной ввод** — POST /api/auth/verify-otp { code }.
2. **Magic link** — GET /api/auth/magic?code=... (бот встраивает код в
   URL-кнопку «Открыть NutriFit»; пользователь кликает → backend
   верифицирует → ставит cookies → 302 на /dashboard).

Оба пути вызывают один и тот же `verify_otp_code`, поэтому OTP
одноразовый: кто первый использовал (клик или ручной ввод) — тот и
залогинен, второй вызов вернёт ошибку.
"""

import logging

from fastapi import APIRouter, HTTPException, Query, Response, Request, status
from fastapi.responses import RedirectResponse

from app.dependencies import DbDep, SettingsDep
from app.models.auth import OTPVerifyRequest, TokenResponse
from app.services import auth_service
from app.services.auth_cookies import set_auth_cookies, clear_auth_cookies

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    body: OTPVerifyRequest,
    db: DbDep,
    settings: SettingsDep,
    request: Request,
    response: Response,
):
    user_id = await auth_service.verify_otp_code(db, body.code)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Код не найден или истёк. Нажми /start в боте, чтобы получить новый.",
        )

    access, refresh = await auth_service.create_session(
        db, user_id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    set_auth_cookies(response, settings, access, refresh)

    # Онбординг нужен тем, у кого ещё не заполнена базовая анкета.
    # Google/Yandex/VK flow проверяет то же самое — см. auth_cookies.needs_onboarding.
    health = await db.fetchrow(
        "SELECT imt FROM user_health WHERE user_id = $1 ORDER BY date DESC LIMIT 1",
        user_id,
    )
    needs_onboarding = health is None

    return TokenResponse(access_token=access, user_id=user_id, needs_onboarding=needs_onboarding)


@router.get("/magic")
async def magic_link(
    request: Request,
    db: DbDep,
    settings: SettingsDep,
    code: str = Query(..., min_length=4, max_length=8),
):
    """Auto-login по клику из Telegram-бота.

    Бот встраивает OTP-код в URL кнопки: /api/auth/magic?code=AB3K7Y.
    Пользователь кликает → мы верифицируем код, создаём сессию, ставим
    cookies и делаем 302 на фронт. Ни одного ручного шага.
    """
    frontend = (settings.FRONTEND_URL or "").rstrip("/")
    login_url = f"{frontend}/login"

    user_id = await auth_service.verify_otp_code(db, code)
    if user_id is None:
        logger.info("Magic link: invalid/expired code")
        return RedirectResponse(
            f"{login_url}?auth_error=invalid_code",
            status_code=302,
        )

    access, refresh = await auth_service.create_session(
        db, user_id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    health = await db.fetchrow(
        "SELECT imt FROM user_health WHERE user_id = $1 ORDER BY date DESC LIMIT 1",
        user_id,
    )
    destination = "/onboarding" if health is None else "/dashboard"

    redirect = RedirectResponse(f"{frontend}{destination}", status_code=302)
    set_auth_cookies(redirect, settings, access, refresh)
    return redirect


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    db: DbDep,
    settings: SettingsDep,
    response: Response,
):
    refresh = request.cookies.get(settings.AUTH_COOKIE_PREFIX + "refresh_token")
    if not refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    result = await auth_service.refresh_session(db, refresh)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access, new_refresh = result
    payload = auth_service.decode_token(access)
    user_id = int(payload["sub"])

    set_auth_cookies(response, settings, access, new_refresh)

    return TokenResponse(access_token=access, user_id=user_id)


@router.post("/logout")
async def logout(
    request: Request,
    db: DbDep,
    settings: SettingsDep,
    response: Response,
):
    prefix = settings.AUTH_COOKIE_PREFIX
    token = request.cookies.get(prefix + "access_token")
    if token:
        await auth_service.invalidate_session(db, token)
    clear_auth_cookies(response, settings)
    return {"message": "Logged out"}
