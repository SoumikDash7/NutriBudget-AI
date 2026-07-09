from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class OTP(BaseModel):
    __tablename__ = "otps"

    email_or_phone: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )

    otp_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    purpose: Mapped[str] = mapped_column(
        String(50),
        default="register",
        nullable=False,
    )

    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
