from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    response: str


class RecipeRequest(BaseModel):
    meal_type: str = Field(pattern="^(breakfast|lunch|dinner)$")
