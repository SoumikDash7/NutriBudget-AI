from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.calorie import (
    CalorieLogCreate,
    CalorieLogResponse,
    CalorieDashboardResponse,
    FoodParseRequest,
    FoodScanResponse,
)
from app.services.calorie_service import CalorieService

router = APIRouter(
    prefix="/calorie",
    tags=["Calorie Calculator"],
)


@router.get(
    "/dashboard",
    response_model=CalorieDashboardResponse,
)
async def get_calorie_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CalorieService(db)
    return await service.get_dashboard(current_user.id)


@router.post(
    "/log",
    response_model=CalorieLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def log_food_entry(
    request: CalorieLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CalorieService(db)
    try:
        return await service.log_food(
            user_id=current_user.id,
            food_name=request.food_name,
            calories=request.calories,
            protein=request.protein,
            carbs=request.carbs,
            fat=request.fat,
            logged_date=request.logged_date,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/parse",
    response_model=FoodScanResponse,
)
async def parse_food_description(
    request: FoodParseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CalorieService(db)
    try:
        return await service.parse_description(request.description)
    except ValueError as e:
        err_msg = str(e)
        if "401" in err_msg or "unauthenticated" in err_msg.lower() or "credentials" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=err_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during description parsing: {str(e)}"
        )


@router.get(
    "/barcode/{barcode}",
    response_model=FoodScanResponse,
)
async def lookup_barcode(
    barcode: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CalorieService(db)
    product = await service.lookup_barcode(barcode)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with barcode '{barcode}' not found in Open Food Facts database."
        )
    return product


@router.post(
    "/scan-image",
    response_model=FoodScanResponse,
)
async def scan_food_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CalorieService(db)
    file_bytes = await file.read()
    try:
        return await service.scan_image(file.filename, file_bytes)
    except ValueError as e:
        err_msg = str(e)
        if "401" in err_msg or "unauthenticated" in err_msg.lower() or "credentials" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=err_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during image scanning: {str(e)}"
        )

