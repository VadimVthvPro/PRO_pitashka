from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    # Optional: when set, the matching active plan is injected into the
    # context block so the user can ask "what should I cook today?" and the
    # assistant answers from the plan instead of inventing one.
    attach: Literal["meal_plan", "workout_plan", None] = None


class ChatResponse(BaseModel):
    response: str
    message_id: int | None = None


class HistoryMessage(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    text: str
    created_at: str


class HistoryResponse(BaseModel):
    messages: list[HistoryMessage]


class RecipeRequest(BaseModel):
    meal_type: str = Field(pattern="^(breakfast|lunch|dinner)$")
