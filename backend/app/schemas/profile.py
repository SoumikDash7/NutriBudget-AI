from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    ActivityLevel,
    Goal,
    PreferredUnit,
    Sex,
)


class ProfileCreateRequest(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=100,
    )

    sex: Sex

    date_of_birth: date

    height_cm: float = Field(
        gt=50,
        lt=300,
    )

    current_weight_kg: float = Field(
        gt=20,
        lt=500,
    )

    goal_weight_kg: float = Field(
        gt=20,
        lt=500,
    )

    goal: Goal

    activity_level: ActivityLevel

    exercise_days_per_week: int = Field(
        ge=0,
        le=7,
    )

    preferred_unit: PreferredUnit = PreferredUnit.METRIC


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = None

    sex: Sex | None = None

    date_of_birth: date | None = None

    height_cm: float | None = Field(
        default=None,
        gt=50,
        lt=300,
    )

    current_weight_kg: float | None = Field(
        default=None,
        gt=20,
        lt=500,
    )

    goal_weight_kg: float | None = Field(
        default=None,
        gt=20,
        lt=500,
    )

    goal: Goal | None = None

    activity_level: ActivityLevel | None = None

    exercise_days_per_week: int | None = Field(
        default=None,
        ge=0,
        le=7,
    )

    preferred_unit: PreferredUnit | None = None


class ProfileResponse(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID

    user_id: UUID

    full_name: str

    sex: Sex

    date_of_birth: date

    height_cm: float

    current_weight_kg: float

    goal_weight_kg: float

    goal: Goal

    activity_level: ActivityLevel

    exercise_days_per_week: int

    preferred_unit: PreferredUnit

    bmi: float

    bmr: float

    tdee: float

    daily_calorie_target: int

    daily_protein_target: float

    daily_carb_target: float

    daily_fat_target: float