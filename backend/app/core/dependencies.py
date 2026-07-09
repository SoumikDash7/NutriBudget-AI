import httpx
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import decode_token, JWTError
from app.db.session import get_db
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:

        payload = decode_token(token)

        user_id = payload.get("sub")
        token_type = payload.get("type")

        if user_id is None or token_type != "access":
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    repo = UserRepository(db)

    try:
        user = await repo.get_by_id(user_id)
    except Exception:
        raise credentials_exception

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise credentials_exception

    return user


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client