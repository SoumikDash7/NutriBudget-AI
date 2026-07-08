from datetime import date
from uuid import UUID

from sqlalchemy import (
    Date,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    ActivityLevel,
    Goal,
    PreferredUnit,
    Sex,
)
from app.db.base import BaseModel


class Profile(BaseModel):
    __tablename__ = "profiles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    sex: Mapped[Sex] = mapped_column(
        Enum(Sex),
        nullable=False,
    )

    date_of_birth: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    height_cm: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    current_weight_kg: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    goal_weight_kg: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    goal: Mapped[Goal] = mapped_column(
        Enum(Goal),
        nullable=False,
    )

    activity_level: Mapped[ActivityLevel] = mapped_column(
        Enum(ActivityLevel),
        nullable=False,
    )

    exercise_days_per_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    preferred_unit: Mapped[PreferredUnit] = mapped_column(
        Enum(PreferredUnit),
        default=PreferredUnit.METRIC,
        nullable=False,
    )

    bmi: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    bmr: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    tdee: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    daily_calorie_target: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    daily_protein_target: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    daily_carb_target: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    daily_fat_target: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="profile",
    )