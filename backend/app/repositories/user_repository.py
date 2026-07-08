from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str):
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str):
        result = await self.db.execute(
            select(User).where(User.phone == phone)
        )
        return result.scalar_one_or_none()

    async def get_by_email_or_phone(
        self,
        email: str | None,
        phone: str | None,
    ):
        conditions = []

        if email:
            conditions.append(User.email == email)

        if phone:
            conditions.append(User.phone == phone)

        if not conditions:
            return None

        result = await self.db.execute(
            select(User).where(or_(*conditions))
        )

        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        user_id: UUID | str,
    ):
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User):
        self.db.add(user)

        await self.db.commit()

        await self.db.refresh(user)

        return user

    async def update_last_login(
        self,
        user: User,
    ):
        user.last_login = datetime.now(timezone.utc)

        await self.db.commit()

        await self.db.refresh(user)

        return user

    async def update_password(
        self,
        user: User,
        password_hash: str,
    ):
        user.password_hash = password_hash

        await self.db.commit()

        await self.db.refresh(user)

        return user