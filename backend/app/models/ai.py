from typing import Literal, Optional

from pydantic import BaseModel, Field


AttachKind = Literal["meal_plan", "workout_plan", None]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    # Optional: when set, the matching active plan is injected into the
    # context block so the user can ask "what should I cook today?" and the
    # assistant answers from the plan instead of inventing one.
    attach: AttachKind = None


class ChatResponse(BaseModel):
    response: str
    message_id: int | None = None
    latency_ms: int | None = None
    model: str | None = None


class HistoryMessage(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    text: str
    created_at: str
    feedback: Optional[int] = None
    attach_kind: Optional[str] = None


class HistoryResponse(BaseModel):
    messages: list[HistoryMessage]


class RecipeRequest(BaseModel):
    meal_type: str = Field(pattern="^(breakfast|lunch|dinner)$")


class FeedbackRequest(BaseModel):
    message_id: int
    value: Literal[-1, 0, 1]


class RegenerateResponse(BaseModel):
    response: str
    message_id: int
    deleted_id: int | None = None
    latency_ms: int | None = None
    model: str | None = None


class QuickPrompt(BaseModel):
    icon: str            # solar:* iconify name
    label: str           # short chip label
    prompt: str          # full message that gets sent to chat
    accent: bool = False # highlight chip if it's the most relevant suggestion


class QuickPromptsResponse(BaseModel):
    prompts: list[QuickPrompt]

