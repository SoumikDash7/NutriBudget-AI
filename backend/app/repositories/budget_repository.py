from datetime import date
from uuid import UUID
from sqlalchemy import select, and_, or_, extract, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import BudgetTransaction, Collaboration, BudgetNotification


class BudgetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Transactions
    async def create_transaction(self, tx: BudgetTransaction) -> BudgetTransaction:
        self.db.add(tx)
        await self.db.commit()
        await self.db.refresh(tx)
        return tx

    async def get_monthly_transactions(
        self,
        user_id: UUID,
        year: int,
        month: int,
    ) -> list[BudgetTransaction]:
        # Fetch active collaborations to get shared transactions too
        active_collabs = await self.get_active_collaborations(user_id)
        collab_ids = [c.id for c in active_collabs]

        # Fetch personal + collaborative transactions
        conditions = [
            extract("year", BudgetTransaction.date) == year,
            extract("month", BudgetTransaction.date) == month,
        ]

        if collab_ids:
            conditions.append(
                or_(
                    BudgetTransaction.user_id == user_id,
                    BudgetTransaction.collaboration_id.in_(collab_ids)
                )
            )
        else:
            conditions.append(BudgetTransaction.user_id == user_id)

        result = await self.db.execute(
            select(BudgetTransaction)
            .where(and_(*conditions))
            .order_by(BudgetTransaction.date.desc())
        )
        return list(result.scalars().all())

    # Collaborations
    async def create_collaboration(self, collab: Collaboration) -> Collaboration:
        self.db.add(collab)
        await self.db.commit()
        await self.db.refresh(collab)
        return collab

    async def get_collaboration_by_id(self, collab_id: UUID) -> Collaboration | None:
        result = await self.db.execute(
            select(Collaboration).where(Collaboration.id == collab_id)
        )
        return result.scalar_one_or_none()

    async def get_active_collaborations(self, user_id: UUID) -> list[Collaboration]:
        result = await self.db.execute(
            select(Collaboration)
            .where(
                and_(
                    or_(Collaboration.owner_id == user_id, Collaboration.partner_id == user_id),
                    Collaboration.status == "accepted"
                )
            )
        )
        return list(result.scalars().all())

    async def get_all_collaborations(self, user_id: UUID) -> list[Collaboration]:
        result = await self.db.execute(
            select(Collaboration)
            .where(or_(Collaboration.owner_id == user_id, Collaboration.partner_id == user_id))
        )
        return list(result.scalars().all())

    async def get_collaboration_between(self, user_a: UUID, user_b: UUID) -> Collaboration | None:
        result = await self.db.execute(
            select(Collaboration)
            .where(
                or_(
                    and_(Collaboration.owner_id == user_a, Collaboration.partner_id == user_b),
                    and_(Collaboration.owner_id == user_b, Collaboration.partner_id == user_a)
                )
            )
        )
        return result.scalars().first()

    async def update_collaboration_status(self, collab: Collaboration, status: str) -> Collaboration:
        collab.status = status
        await self.db.commit()
        await self.db.refresh(collab)
        return collab

    # Notifications
    async def create_notification(self, notif: BudgetNotification) -> BudgetNotification:
        self.db.add(notif)
        await self.db.commit()
        await self.db.refresh(notif)
        return notif

    async def get_notifications(self, user_id: UUID) -> list[BudgetNotification]:
        result = await self.db.execute(
            select(BudgetNotification)
            .where(BudgetNotification.user_id == user_id)
            .order_by(BudgetNotification.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_notifications_as_read(self, user_id: UUID) -> None:
        await self.db.execute(
            update(BudgetNotification)
            .where(and_(BudgetNotification.user_id == user_id, BudgetNotification.is_read == False))
            .values(is_read=True)
        )
        await self.db.commit()
