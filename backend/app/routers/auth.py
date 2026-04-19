from fastapi import APIRouter, HTTPException, Response, Request, status
from app.dependencies import DbDep, SettingsDep
from app.models.auth import OTPRequest, OTPVerify, TokenResponse
from app.services import auth_service

router = APIRouter()


@router.post("/request-otp")
async def request_otp(body: OTPRequest, db: DbDep):
    code = await auth_service.request_otp(db, body.telegram_username)
    if not code:
        raise HTTPException(status_code=500, detail="Failed to generate OTP")

    user_row = await db.fetchrow(
        "SELECT user_id FROM user_main WHERE telegram_username = $1",
        body.telegram_username.lower(),
    )

    sent = False
    if user_row:
        from telegram_bot.bot import send_otp_message
        sent = await send_otp_message(user_row["user_id"], code)

    return {"message": "OTP sent" if sent else "OTP created (user not found in bot yet)", "sent": sent}


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(body: OTPVerify, db: DbDep, settings: SettingsDep, request: Request, response: Response):
    user_id = await auth_service.verify_otp(db, body.telegram_username, body.code)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP")

    access, refresh = await auth_service.create_session(
        db, user_id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    _set_auth_cookies(response, settings, access, refresh)

    health = await db.fetchrow(
        "SELECT imt FROM user_health WHERE user_id = $1 ORDER BY date DESC LIMIT 1", user_id
    )
    needs_onboarding = health is None

    return TokenResponse(access_token=access, user_id=user_id, needs_onboarding=needs_onboarding)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, db: DbDep, settings: SettingsDep, response: Response):
    refresh = request.cookies.get("refresh_token")
    if not refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    result = await auth_service.refresh_session(db, refresh)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access, new_refresh = result
    payload = auth_service.decode_token(access)
    user_id = int(payload["sub"])

    _set_auth_cookies(response, settings, access, new_refresh)

    return TokenResponse(access_token=access, user_id=user_id)


@router.post("/logout")
async def logout(request: Request, db: DbDep, response: Response):
    token = request.cookies.get("access_token")
    if token:
        await auth_service.invalidate_session(db, token)
    response.delete_cookie("access_token", path="/")
    # Delete refresh on both the new path (/) and the legacy path
    # (/api/auth/refresh) to clean up cookies issued before the path migration.
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth/refresh")
    return {"message": "Logged out"}


def _set_auth_cookies(response: Response, settings, access: str, refresh: str) -> None:
    """Issue auth cookies on the SAME path so the Next.js middleware can do
    silent refresh from any protected route (was a major source of bogus
    "redirected to /login on every navigation" bugs)."""
    secure = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key="access_token", value=access,
        httponly=True, secure=secure, samesite="lax", path="/",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token", value=refresh,
        httponly=True, secure=secure, samesite="lax", path="/",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
