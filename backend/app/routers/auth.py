"""Auth endpoints: Telegram OTP verification, refresh, logout.

Telegram-flow теперь состоит из одного шага со стороны сайта:

    1. Пользователь кликает «Войти через Telegram» → открывается бот.
    2. В боте нажимает /start → бот создаёт OTP, привязанный к его
       telegram user_id, и присылает 6-значный код (с кнопкой «Прислать
       новый ключ» на случай, если пользователь закрыл сообщение).
    3. На сайте пользователь вставляет код → POST /api/auth/verify-otp
       → JWT/session cookies выставлены, редирект на /dashboard или
       /onboarding.

Никаких `@username`-инпутов, никакого `request-otp` на сайте — если
пользователь хочет «переслать ещё один код», он делает это в самом боте.
Это решение принято осознанно: сайт не должен знать Telegram-username
пользователя, а OTP должен привязываться к идентичности пользователя
в Telegram (user_id), а не к mutable @username.
"""

from fastapi import APIRouter, HTTPException, Response, Request, status

from app.dependencies import DbDep, SettingsDep
from app.models.auth import OTPVerifyRequest, TokenResponse
from app.services import auth_service
from app.services.auth_cookies import set_auth_cookies, clear_auth_cookies

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
