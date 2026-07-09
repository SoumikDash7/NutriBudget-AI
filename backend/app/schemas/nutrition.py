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
    quantity: float
    unit: str


class NutritionEstimate(BaseModel):
    ingredients: list[ExtractedIngredient]
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence: float = Field(ge=0.0, le=1.0)
    source_provider: Optional[str] = None

    @field_validator("calories")
    @classmethod
    def sane_calories(cls, v):
        if v < 0 or v > 10000:
            raise ValueError("calories out of plausible range")
        return v


class ProviderResponse(BaseModel):
    raw_text: str
    data: dict