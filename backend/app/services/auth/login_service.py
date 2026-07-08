from app.core.jwt import (
    create_access_token,
    create_refresh_token,
)
from app.core.security import verify_password
from app.repositories.user_repository import UserRepository
from app.core.exceptions import InvalidCredentialsException


class LoginService:

    def __init__(self, db):
        self.repo = UserRepository(db)

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

        if user is None:
            raise InvalidCredentialsException()

        if not verify_password(
            password,
            user.password_hash,
        ):
            raise InvalidCredentialsException()

        return {
            "user": user,
            "tokens": {
                "access_token": create_access_token(str(user.id)),
                "refresh_token": create_refresh_token(str(user.id)),
                "token_type": "bearer",
            },
        }