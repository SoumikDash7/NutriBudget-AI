from datetime import date
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import BudgetTransaction, Collaboration, BudgetNotification
from app.repositories.budget_repository import BudgetRepository
from app.repositories.user_repository import UserRepository


class BudgetService:
    def __init__(self, db: AsyncSession):
        self.repo = BudgetRepository(db)
        self.user_repo = UserRepository(db)

    async def add_transaction(
        self,
        user_id: UUID,
        amount: float,
        reason: str,
        category: str,
        tx_date: date,
        is_collaborative: bool = False,
        collaboration_id: UUID | None = None,
    ) -> BudgetTransaction:
        tx = BudgetTransaction(
            user_id=user_id,
            amount=amount,
            reason=reason,
            category=category,
            date=tx_date,
            is_collaborative=is_collaborative,
            collaboration_id=collaboration_id,
        )

        created_tx = await self.repo.create_transaction(tx)

        # Handle collaboration notifications
        if is_collaborative and collaboration_id:
            collab = await self.repo.get_collaboration_by_id(collaboration_id)
            if collab and collab.status == "accepted":
                creator = await self.user_repo.get_by_id(user_id)
                creator_name = creator.email or creator.phone or "Someone"

                # Identify the other person to notify
                recipient_id = collab.partner_id if user_id == collab.owner_id else collab.owner_id

                notification_message = (
                    f"{creator_name} added an expense of ${amount:.2f} for '{reason}' "
                    f"in the shared budget '{collab.name}'."
                )

                notif = BudgetNotification(
                    user_id=recipient_id,
                    type="spending_added",
                    message=notification_message,
                    is_read=False,
                )
                await self.repo.create_notification(notif)

        return created_tx

    async def get_monthly_dashboard(self, user_id: UUID, year: int, month: int) -> dict:
        transactions = await self.repo.get_monthly_transactions(user_id, year, month)
        collaborations = await self.repo.get_all_collaborations(user_id)
        notifications = await self.repo.get_notifications(user_id)

        personal_total = sum(t.amount for t in transactions if not t.is_collaborative)
        collaborative_total = sum(t.amount for t in transactions if t.is_collaborative)
        monthly_total = personal_total + collaborative_total

        return {
            "monthly_total":      monthly_total,
            "personal_total":     personal_total,
            "collaborative_total": collaborative_total,
            "transactions":       transactions,
            "collaborations":     collaborations,
            "notifications":      notifications,
        }

    async def send_collaboration_invite(
        self,
        owner_id: UUID,
        partner_email_or_phone: str,
        name: str = "Shared Budget",
    ) -> Collaboration:
        partner = await self.user_repo.get_by_email_or_phone(
            email=partner_email_or_phone if "@" in partner_email_or_phone else None,
            phone=partner_email_or_phone if "@" not in partner_email_or_phone else None,
        )

        if partner is None:
            raise ValueError(f"User with identifier '{partner_email_or_phone}' not found.")

        if partner.id == owner_id:
            raise ValueError("You cannot collaborate with yourself.")

        existing = await self.repo.get_collaboration_between(owner_id, partner.id)
        if existing:
            if existing.status == "pending":
                raise ValueError("A collaboration request is already pending between you two.")
            elif existing.status == "accepted":
                raise ValueError("You are already collaborating with this user.")
            else:
                # Reset status to pending
                return await self.repo.update_collaboration_status(existing, "pending")

        collab = Collaboration(
            owner_id=owner_id,
            partner_id=partner.id,
            status="pending",
            name=name,
        )

        created_collab = await self.repo.create_collaboration(collab)

        # Notify the partner
        owner = await self.user_repo.get_by_id(owner_id)
        owner_name = owner.email or owner.phone or "Someone"

        invite_message = f"{owner_name} invited you to collaborate on the shared budget '{name}'."
        notif = BudgetNotification(
            user_id=partner.id,
            type="collaboration_invite",
            message=invite_message,
            is_read=False,
        )
        await self.repo.create_notification(notif)

        return created_collab

    async def respond_to_invite(
        self,
        partner_id: UUID,
        collab_id: UUID,
        status: str,
    ) -> Collaboration:
        collab = await self.repo.get_collaboration_by_id(collab_id)

        if collab is None:
            raise ValueError("Collaboration request not found.")

        if collab.partner_id != partner_id:
            raise ValueError("You are not authorized to respond to this invite.")

        if collab.status != "pending":
            raise ValueError(f"Invitation has already been {collab.status}.")

        updated_collab = await self.repo.update_collaboration_status(collab, status)

        # Notify the owner
        partner = await self.user_repo.get_by_id(partner_id)
        partner_name = partner.email or partner.phone or "Someone"

        notification_message = f"{partner_name} {status} your invitation to collaborate on '{collab.name}'."
        notif = BudgetNotification(
            user_id=collab.owner_id,
            type="collaboration_invite",
            message=notification_message,
            is_read=False,
        )
        await self.repo.create_notification(notif)

        return updated_collab

    async def get_notifications(self, user_id: UUID) -> list[BudgetNotification]:
        return await self.repo.get_notifications(user_id)

    async def mark_notifications_as_read(self, user_id: UUID) -> None:
        await self.repo.mark_notifications_as_read(user_id)
