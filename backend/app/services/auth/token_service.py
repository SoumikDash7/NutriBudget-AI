from jose import JWTError

from app.core.jwt import (
    create_access_token,
    decode_token,
)
from app.repositories.user_repository import UserRepository


class TokenService:

    def __init__(self, db):
        self.repo = UserRepository(db)

    async def refresh(
        self,
        refresh_token: str,
    ):

        try:
            payload = decode_token(refresh_token)

        except JWTError:
            raise ValueError("Invalid refresh token.")

        if payload.get("type") != "refresh":
            raise ValueError("Invalid refresh token.")

        user = await self.repo.get_by_id(
            payload["sub"]
        )

        if user is None:
            raise ValueError("User not found.")

        return {
            "access_token": create_access_token(
                str(user.id)
            ),
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }