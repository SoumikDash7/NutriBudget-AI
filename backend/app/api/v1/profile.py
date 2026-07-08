from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.profile import (
    ProfileCreateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.services.profile_service import ProfileService

router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
)


@router.post(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(
    request: ProfileCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = ProfileService(db)

        return await service.create_profile(
            current_user,
            request,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get(
    "/me",
    response_model=ProfileResponse,
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = ProfileService(db)

        return await service.get_my_profile(
            current_user
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


@router.patch(
    "",
    response_model=ProfileResponse,
)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = ProfileService(db)

        return await service.update_profile(
            current_user,
            request,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )