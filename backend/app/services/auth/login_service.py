from app.core.jwt import (
    create_access_token,
    create_refresh_token,
)
from app.core.logging import get_logger
from app.core.security import verify_password
from app.repositories.user_repository import UserRepository
from app.core.exceptions import InvalidCredentialsException

logger = get_logger(__name__)


class LoginService:

    def __init__(self, db):
        self.repo = UserRepository(db)

    async def login(
        self,
        email: str | None,
        phone: str | None,
        password: str,
    ):
        identifier = email or phone or "<unknown>"
        logger.info(f"login: attempt for identifier='{identifier}'")

        user = await self.repo.get_by_email_or_phone(
            email=email,
            phone=phone,
        )

        if user is None:
            logger.warning(f"login: user not found for identifier='{identifier}'")
            raise InvalidCredentialsException()

        if not verify_password(password, user.password_hash):
            logger.warning(f"login: wrong password for identifier='{identifier}'  user_id={user.id}")
            raise InvalidCredentialsException()

        if not user.is_active:
            logger.warning(f"login: account deactivated for identifier='{identifier}'  user_id={user.id}")
            raise InvalidCredentialsException()

        logger.info(f"login: success  user_id={user.id}  identifier='{identifier}'")

        return {
            "user": user,
            "tokens": {
                "access_token": create_access_token(str(user.id)),
                "refresh_token": create_refresh_token(str(user.id)),
                "token_type": "bearer",
            },
        }