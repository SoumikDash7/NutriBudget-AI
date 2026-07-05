from app.core.jwt import (
    create_access_token,
    create_refresh_token,
)
from app.core.security import hash_password
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