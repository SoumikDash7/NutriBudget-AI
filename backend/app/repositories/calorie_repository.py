from datetime import date, timedelta
from uuid import UUID
from typing import cast
from sqlalchemy import select, and_, delete, CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calorie import CalorieLog


class CalorieRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(self, log: CalorieLog) -> CalorieLog:
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def get_logs_for_date(self, user_id: UUID, query_date: date) -> list[CalorieLog]:
        result = await self.db.execute(
            select(CalorieLog)
            .where(
                and_(
                    CalorieLog.user_id == user_id,
                    CalorieLog.logged_date == query_date,
                )
            )
            .order_by(CalorieLog.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_logs_past_days(self, user_id: UUID, days: int = 7) -> list[CalorieLog]:
        start_date = date.today() - timedelta(days=days - 1)
        result = await self.db.execute(
            select(CalorieLog)
            .where(
                and_(
                    CalorieLog.user_id == user_id,
                    CalorieLog.logged_date >= start_date,
                )
            )
            .order_by(CalorieLog.logged_date.desc(), CalorieLog.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_logs_older_than(self, user_id: UUID, days: int = 7) -> int:
        cutoff_date = date.today() - timedelta(days=days)
        result = await self.db.execute(
            delete(CalorieLog).where(
                and_(
                    CalorieLog.user_id == user_id,
                    CalorieLog.logged_date < cutoff_date,
                )
            )
        )
        await self.db.commit()
        return cast(CursorResult, result).rowcount or 0
