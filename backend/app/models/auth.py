"""Auth request/response models shared across auth providers.

После миграции на user_id-based OTP (см. alembic 017) `OTPVerifyRequest`
принимает ТОЛЬКО 6-символьный код — никакого telegram_username: поиск
идёт по partial-unique `otp_codes.code WHERE used=FALSE`.

`TokenResponse.needs_onboarding` используется фронтом, чтобы понять,
куда редиректить после логина: на `/onboarding` (если пользователь ещё
не заполнил рост/вес) или сразу на `/dashboard`.
"""
from pydantic import BaseModel, Field


class OTPVerifyRequest(BaseModel):
    code: str = Field(min_length=4, max_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    needs_onboarding: bool = False
