from pydantic import BaseModel


class WaterResponse(BaseModel):
    count: int
    ml: int
