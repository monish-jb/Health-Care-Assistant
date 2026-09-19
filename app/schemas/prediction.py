from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    symptoms: list[str] = Field(..., min_length=1, max_length=30)


class ConditionScore(BaseModel):
    condition: str
    confidence: float


class PredictionResponse(BaseModel):
    possible_conditions: list[ConditionScore]
    unrecognized_symptoms: list[str] = []
    disclaimer: str
