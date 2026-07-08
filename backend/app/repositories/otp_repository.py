from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.otp import OTP


class OTPRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, otp: OTP) -> OTP:
        self.db.add(otp)
        await self.db.commit()
        await self.db.refresh(otp)
        return otp

    async def get_latest_active_otp(
        self,
        email_or_phone: str,
        purpose: str,
    ) -> OTP | None:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(OTP)
            .where(
                and_(
                    OTP.email_or_phone == email_or_phone,
                    OTP.purpose == purpose,
                    OTP.verified == False,
                    OTP.expires_at > now,
                )
            )
            .order_by(OTP.created_at.desc())
        )
        return result.scalars().first()

    async def mark_verified(self, otp: OTP) -> OTP:
        otp.verified = True
        await self.db.commit()
        await self.db.refresh(otp)
        return otp
