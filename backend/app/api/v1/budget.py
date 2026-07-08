from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.budget import (
    BudgetTransactionCreate,
    BudgetTransactionResponse,
    CollaborationCreate,
    CollaborationResponse,
    CollaborationUpdate,
    BudgetDashboardResponse,
)

from app.services.budget_service import BudgetService

router = APIRouter(
    prefix="/budget",
    tags=["Budget Calculator"],
)


@router.get(
    "/dashboard",
    response_model=BudgetDashboardResponse,
)
async def get_budget_dashboard(
    year: int | None = None,
    month: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = BudgetService(db)
    today = date.today()
    y = year or today.year
    m = month or today.month

    return await service.get_monthly_dashboard(
        user_id=current_user.id,
        year=y,
        month=m,
    )


@router.post(
    "/transaction",
    response_model=BudgetTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_budget_transaction(
    request: BudgetTransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = BudgetService(db)
    try:
        return await service.add_transaction(
            user_id=current_user.id,
            amount=request.amount,
            reason=request.reason,
            category=request.category,
            tx_date=request.date,
            is_collaborative=request.is_collaborative,
            collaboration_id=request.collaboration_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/invite",
    response_model=CollaborationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_collaboration_invite(
    request: CollaborationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = BudgetService(db)
    try:
        return await service.send_collaboration_invite(
            owner_id=current_user.id,
            partner_email_or_phone=request.partner_email_or_phone,
            name=request.name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/invite/{collab_id}/respond",
    response_model=CollaborationResponse,
)
async def respond_to_collaboration_invite(
    collab_id: UUID,
    request: CollaborationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = BudgetService(db)
    try:
        return await service.respond_to_invite(
            partner_id=current_user.id,
            collab_id=collab_id,
            status=request.status,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/notifications/read",
    response_model=MessageResponse,
)
async def mark_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = BudgetService(db)
    await service.mark_notifications_as_read(current_user.id)
    return {"message": "Notifications marked as read."}
