import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.otp import OTP
from app.repositories.otp_repository import OTPRepository


class OTPService:
    def __init__(self, db: AsyncSession):
        self.repo = OTPRepository(db)

    async def generate_and_send_otp(
        self,
        email_or_phone: str,
        purpose: str = "register",
    ) -> str:
        # Generate 6-digit OTP code
        otp_code = "".join(random.choices("0123456789", k=6))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        otp = OTP(
            email_or_phone=email_or_phone,
            otp_code=otp_code,
            expires_at=expires_at,
            purpose=purpose,
            verified=False,
        )

        await self.repo.create(otp)

        # Mock send: Print to console for verification
        print("\n" + "=" * 50)
        print(f" MOCK OTP SENT TO: {email_or_phone}")
        print(f" PURPOSE: {purpose}")
        print(f" OTP CODE: {otp_code}")
        print("=" * 50 + "\n")

        return otp_code

    async def verify_otp(
        self,
        email_or_phone: str,
        otp_code: str,
        purpose: str = "register",
    ) -> bool:
        active_otp = await self.repo.get_latest_active_otp(email_or_phone, purpose)

        if active_otp is None:
            return False

        if active_otp.otp_code != otp_code:
            return False

        await self.repo.mark_verified(active_otp)
        return True
