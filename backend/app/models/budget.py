from datetime import date
from uuid import UUID

from sqlalchemy import Boolean, Date, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class Collaboration(BaseModel):
    __tablename__ = "collaborations"

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",  # pending, accepted, rejected
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        default="Shared Budget",
        nullable=False,
    )

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], backref="owned_collaborations")
    partner = relationship("User", foreign_keys=[partner_id], backref="partnered_collaborations")


class BudgetTransaction(BaseModel):
    __tablename__ = "budget_transactions"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    is_collaborative: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    collaboration_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("collaborations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    user = relationship("User", backref="budget_transactions")
    collaboration = relationship("Collaboration", backref="transactions")


class BudgetNotification(BaseModel):
    __tablename__ = "budget_notifications"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type: Mapped[str] = mapped_column(
        String(50),  # collaboration_invite, spending_added
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    user = relationship("User", backref="budget_notifications")
