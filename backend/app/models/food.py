from pydantic import BaseModel, Field
from datetime import date


class FoodManualRequest(BaseModel):
    foods: list[str] = Field(min_length=1)
    grams: list[float] = Field(min_length=1)
    food_date: date = Field(default_factory=date.today)


class FoodItem(BaseModel):
    name: str
    grams: float = 0
    cal: float
    protein: float = Field(alias="b", default=0)
    fat: float = Field(alias="g", default=0)
    carbs: float = Field(alias="u", default=0)

    model_config = {"populate_by_name": True}


class FoodDayTotals(BaseModel):
    total_cal: float
    total_protein: float
    total_fat: float
    total_carbs: float
