from app.core.security import hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.services.otp_service import OTPService


class PasswordService:

    def __init__(self, db):
        self.repo = UserRepository(db)
        self.otp_service = OTPService(db)

    async def change_password(
        self,
        user,
        current_password: str,
        new_password: str,
    ):

        # Verify current password
        if not verify_password(
            current_password,
            user.password_hash,
        ):
            raise ValueError("Current password is incorrect.")

        # Hash the new password
        new_password_hash = hash_password(
            new_password
        )

        # Save it in database
        await self.repo.update_password(
            user,
            new_password_hash,
        )

        return {
            "message": "Password changed successfully."
        }

    async def forgot_password(
        self,
        email_or_phone: str,
    ):
        # 1. Look up user
        user = await self.repo.get_by_email_or_phone(
            email=email_or_phone if "@" in email_or_phone else None,
            phone=email_or_phone if "@" not in email_or_phone else None,
        )

        if not user:
            raise ValueError("User with this identifier does not exist.")

        # 2. Generate reset OTP
        otp_code = await self.otp_service.generate_and_send_otp(
            email_or_phone=email_or_phone,
            purpose="reset_password",
        )

        return {
            "message": f"OTP sent to {email_or_phone}.",
            "otp_code": otp_code,  # returned in dev env for testing ease
        }

    async def reset_password(
        self,
        email_or_phone: str,
        otp_code: str,
        new_password: str,
    ):
        # 1. Verify OTP
        otp_ok = await self.otp_service.verify_otp(
            email_or_phone=email_or_phone,
            otp_code=otp_code,
            purpose="reset_password",
        )

        if not otp_ok:
            raise ValueError("Invalid or expired OTP. Please request a new one.")

        # 2. Get user
        user = await self.repo.get_by_email_or_phone(
            email=email_or_phone if "@" in email_or_phone else None,
            phone=email_or_phone if "@" not in email_or_phone else None,
        )

        if not user:
            raise ValueError("User not found.")

        # 3. Hash and update password
        new_password_hash = hash_password(new_password)
        await self.repo.update_password(user, new_password_hash)

        return {
            "message": "Password has been reset successfully."
        }