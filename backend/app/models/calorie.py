from datetime import date
from uuid import UUID

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class CalorieLog(BaseModel):
    __tablename__ = "calorie_logs"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    food_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    calories: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    protein: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    carbs: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    fat: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    logged_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    user = relationship(
        "User",
        backref="calorie_logs",
    )
