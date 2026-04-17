from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


class OnboardingRequest(BaseModel):
    height: float = Field(gt=50, lt=300)
    weight: float = Field(gt=20, lt=500)
    date_of_birth: date
    sex: str = Field(pattern="^[MF]$")
    aim: str = Field(pattern="^(weight_loss|maintain|weight_gain)$")


class OnboardingResponse(BaseModel):
    bmi: float
    bmi_class: str
    daily_cal: float


class ProfileResponse(BaseModel):
    user_id: int
    user_name: Optional[str] = None
    user_sex: Optional[str] = None
    date_of_birth: Optional[date] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    bmi: Optional[float] = None
    bmi_class: Optional[str] = None
    daily_cal: Optional[float] = None
    aim: Optional[str] = None
    lang: str = "ru"


class UpdateProfileRequest(BaseModel):
    weight: Optional[float] = Field(default=None, gt=20, lt=500)
    height: Optional[float] = Field(default=None, gt=50, lt=300)


class SettingsRequest(BaseModel):
    theme: Optional[str] = Field(default=None, pattern="^(light|dark|auto)$")
    notifications: Optional[bool] = None
    language: Optional[str] = Field(default=None, pattern="^(ru|en|de|fr|es)$")
