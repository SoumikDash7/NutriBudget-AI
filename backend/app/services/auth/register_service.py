from app.core.jwt import (
    create_access_token,
    create_refresh_token,
)
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.core.exceptions import UserAlreadyExistsException
from app.services.otp_service import OTPService

logger = get_logger(__name__)


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
        identifier = email if email else phone
        if not identifier:
            raise ValueError("Email or phone must be provided.")

        logger.info(f"register: attempt for identifier='{identifier}'")

        # 1. Verify OTP
        logger.debug(f"Verifying OTP for '{identifier}' (purpose=register)")
        otp_ok = await self.otp_service.verify_otp(
            email_or_phone=identifier,
            otp_code=otp_code,
            purpose="register",
        )
        if not otp_ok:
            logger.warning(f"OTP verification failed for '{identifier}'")
            raise ValueError("Invalid or expired OTP. Please try again.")

        logger.debug(f"OTP verified for '{identifier}'")

        # 2. Check for duplicate
        existing = await self.repo.get_by_email_or_phone(email=email, phone=phone)
        if existing:
            logger.warning(f"Registration rejected — user already exists: '{identifier}'")
            raise UserAlreadyExistsException()

        # 3. Create user
        user = User(
            email=email,
            phone=phone,
            password_hash=hash_password(password),
            email_verified=email is not None,
            phone_verified=phone is not None,
        )
        user = await self.repo.create(user)
        logger.info(f"User registered: id={user.id}  identifier='{identifier}'")

        return {
            "user": user,
            "tokens": {
                "access_token": create_access_token(str(user.id)),
                "refresh_token": create_refresh_token(str(user.id)),
                "token_type": "bearer",
            },
        }