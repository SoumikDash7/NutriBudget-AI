from app.core.jwt import (
    create_access_token,
    create_refresh_token,
)
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.core.exceptions import UserAlreadyExistsException
from app.services.otp_service import OTPService


class RegisterService:

    def __init__(self, db):
        self.repo = UserRepository(db)
        self.otp_service = OTPService(db)

    async def register(
        self,
        email: str | None,
        phone: str | None,
        password: str,
        otp_code: str,
    ):
        # 1. Verify OTP first
        identifier = email if email else phone
        if not identifier:
            raise ValueError("Email or phone must be provided.")

        otp_ok = await self.otp_service.verify_otp(
            email_or_phone=identifier,
            otp_code=otp_code,
            purpose="register",
        )
        if not otp_ok:
            raise ValueError("Invalid or expired OTP. Please try again.")

        # 2. Check if user already exists
        existing = await self.repo.get_by_email_or_phone(
            email=email,
            phone=phone,
        )

        if existing:
            raise UserAlreadyExistsException()

        user = User(
            email=email,
            phone=phone,
            password_hash=hash_password(password),
            email_verified=email is not None,
            phone_verified=phone is not None,
        )

        user = await self.repo.create(user)

        return {
            "user": user,
            "tokens": {
                "access_token": create_access_token(str(user.id)),
                "refresh_token": create_refresh_token(str(user.id)),
                "token_type": "bearer",
            },
        }