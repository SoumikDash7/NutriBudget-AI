from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CalorieLogCreate(BaseModel):
    food_name: str = Field(..., min_length=1, max_length=255)
    calories: int = Field(..., ge=0)
    protein: float = Field(default=0.0, ge=0.0)
    carbs: float = Field(default=0.0, ge=0.0)
    fat: float = Field(default=0.0, ge=0.0)
    logged_date: date


class CalorieLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    food_name: str
    calories: int
    protein: float
    carbs: float
    fat: float
    logged_date: date
    created_at: datetime


class CalorieDashboardResponse(BaseModel):
    target_calories: int
    consumed_calories: int
    remaining_calories: int
    target_protein: float
    consumed_protein: float
    target_carbs: float
    consumed_carbs: float
    target_fat: float
    consumed_fat: float
    logs: list[CalorieLogResponse]
    history_7_days: list[dict]  # list of {date: date, calories: int}


class FoodParseRequest(BaseModel):
    description: str = Field(..., min_length=1)


class ExtractedIngredientResponse(BaseModel):
    """Per-ingredient breakdown surfaced from the AI orchestrator/local DB/OFF results."""
    name: str
    quantity: float = 1.0
    unit: str = "serving"


class FoodScanResponse(BaseModel):
    food_name: str
    calories: int
    protein: float
    carbs: float
    fat: float
    confidence: float = 1.0
    # Optional so existing callers (Local DB fallback, OFF search, barcode lookup)
    # that don't populate a per-ingredient breakdown still validate cleanly -
    # they'll just come back as an empty list rather than failing response
    # validation or getting silently stripped like before this field existed.
    ingredients: list[ExtractedIngredientResponse] = Field(default_factory=list)


class BarcodeScanRequest(BaseModel):
    barcode: str = Field(..., min_length=1)