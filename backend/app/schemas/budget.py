from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class BudgetTransactionCreate(BaseModel):
    amount: float = Field(..., gt=0)
    reason: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    date: date
    is_collaborative: bool = False
    collaboration_id: UUID | None = None


class BudgetTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    amount: float
    reason: str
    category: str
    date: date
    is_collaborative: bool
    collaboration_id: UUID | None
    created_at: datetime


class CollaborationCreate(BaseModel):
    partner_email_or_phone: str = Field(..., min_length=1)
    name: str = "Shared Budget"


class CollaborationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    partner_id: UUID
    status: str
    name: str
    created_at: datetime


class CollaborationUpdate(BaseModel):
    status: str = Field(..., pattern="^(accepted|rejected)$")


class BudgetNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    type: str
    message: str
    is_read: bool
    created_at: datetime


class BudgetDashboardResponse(BaseModel):
    monthly_total: float
    personal_total: float
    collaborative_total: float
    transactions: list[BudgetTransactionResponse]
    collaborations: list[CollaborationResponse]
    notifications: list[BudgetNotificationResponse]
