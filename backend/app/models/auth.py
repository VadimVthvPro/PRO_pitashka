from pydantic import BaseModel, Field


class OTPRequest(BaseModel):
    telegram_username: str = Field(min_length=1, max_length=255)


class OTPVerify(BaseModel):
    telegram_username: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=4, max_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    needs_onboarding: bool = False
