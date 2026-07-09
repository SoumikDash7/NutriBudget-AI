from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.security import (
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:

    def __init__(self, db):
        self.repo = UserRepository(db)

    async def register(
        self,
        email: str | None,
        phone: str | None,
        password: str,
    ):

        existing = await self.repo.get_by_email_or_phone(
            email=email,
            phone=phone,
        )

        if existing:
            raise ValueError(
                "User already exists."
            )

        user = User(
            email=email,
            phone=phone,
            password_hash=hash_password(password),
        )

        user = await self.repo.create(user)

        return {
            "user": user,
            "tokens": {
                "access_token": create_access_token(
                    str(user.id)
                ),
                "refresh_token": create_refresh_token(
                    str(user.id)
                ),
                "token_type": "bearer",
            },
        }

    async def login(
        self,
        email: str | None,
        phone: str | None,
        password: str,
    ):

        user = await self.repo.get_by_email_or_phone(
            email=email,
            phone=phone,
        )

        if not user:
            raise ValueError("Invalid credentials.")

        if not verify_password(
            password,
            user.password_hash,
        ):
            raise ValueError("Invalid credentials.")

        await self.repo.update_last_login(user)

        return {
            "user": user,
            "tokens": {
                "access_token": create_access_token(
                    str(user.id)
                ),
                "refresh_token": create_refresh_token(
                    str(user.id)
                ),
                "token_type": "bearer",
            },
        }

    async def refresh_token(
        self,
        refresh_token: str,
    ):

        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise ValueError("Invalid refresh token.")

        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid refresh token.")

        user = await self.repo.get_by_id(user_id)

        if user is None:
            raise ValueError("User not found.")

        return {
            "access_token": create_access_token(
                str(user.id)
            ),
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }