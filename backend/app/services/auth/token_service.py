from app.core.jwt import (
    create_access_token,
    decode_token,
    JWTError,
)
from app.core.logging import get_logger
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)


class TokenService:

    def __init__(self, db):
        self.repo = UserRepository(db)

    async def refresh_token(self, refresh_token: str):
        logger.debug("refresh_token: decoding token")
        try:
            payload = decode_token(refresh_token)
        except JWTError as e:
            logger.warning(f"refresh_token: invalid JWT — {e}")
            raise ValueError("Invalid refresh token.")

        if payload.get("type") != "refresh":
            logger.warning("refresh_token: token type is not 'refresh'")
            raise ValueError("Invalid refresh token.")

        user = await self.repo.get_by_id(payload["sub"])
        if user is None:
            logger.warning(f"refresh_token: user not found  sub={payload['sub']}")
            raise ValueError("User not found.")

        logger.info(f"refresh_token: issued new access token  user_id={user.id}")
        return {
            "access_token":  create_access_token(str(user.id)),
            "refresh_token": refresh_token,
            "token_type":    "bearer",
        }