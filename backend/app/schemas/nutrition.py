from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Optional


class InputType(str, Enum):
    IMAGE = "image"
    TEXT = "text"


class FoodInput(BaseModel):
    input_type: InputType
    text: Optional[str] = None
    image_base64: Optional[str] = None
    filename: Optional[str] = None

    @field_validator("text")
    @classmethod
    def text_required_for_text_input(cls, v, info):
        if info.data.get("input_type") == InputType.TEXT and not v:
            raise ValueError("text is required when input_type is TEXT")
        return v


class ExtractedIngredient(BaseModel):
    name: str
    # Defaults let callers build a minimal ingredient (e.g. a fallback flat
    # "food_name" with no explicit amount) without needing to invent values.
    quantity: float = 1.0
    unit: str = "serving"


class NutritionEstimate(BaseModel):
    ingredients: list[ExtractedIngredient]
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence: float = Field(ge=0.0, le=1.0)
    source_provider: Optional[str] = None

    @field_validator("ingredients")
    @classmethod
    def ingredients_not_empty(cls, v):
        if not v:
            raise ValueError("ingredients list cannot be empty")
        return v

    @field_validator("calories")
    @classmethod
    def sane_calories(cls, v):
        if v < 0 or v > 10000:
            raise ValueError("calories out of plausible range")
        return v


class ProviderResponse(BaseModel):
    raw_text: str
    data: dict