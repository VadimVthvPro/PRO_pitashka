from pydantic import BaseModel, Field
from datetime import date


class WorkoutSaveRequest(BaseModel):
    training_type_id: int
    duration_minutes: int = Field(gt=0, le=600)
    workout_date: date = Field(default_factory=date.today)


class WorkoutType(BaseModel):
    id: int
    name: str
    emoji: str
    description: str = ""
    base_coefficient: float


class CustomWorkoutRequest(BaseModel):
    description: str = Field(min_length=3, max_length=2000)
    workout_date: date = Field(default_factory=date.today)


class WorkoutSaveResponse(BaseModel):
    training_name: str
    duration: int
    calories: float
    total_today_cal: float
    total_today_duration: int
