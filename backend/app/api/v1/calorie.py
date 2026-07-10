import httpx
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_http_client
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
from app.core.rate_limit import InMemoryRateLimiter

router = APIRouter(
    prefix="/calorie",
    tags=["Calorie Calculator"],
)

ai_rate_limiter = InMemoryRateLimiter(requests_limit=10, window_seconds=60)


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
    http_client: httpx.AsyncClient = Depends(get_http_client),
):
    if not ai_rate_limiter.is_allowed(str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Max 10 requests per minute.",
        )
    service = CalorieService(db, http_client=http_client)
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
    http_client: httpx.AsyncClient = Depends(get_http_client),
):
    service = CalorieService(db, http_client=http_client)
    product = await service.lookup_barcode(barcode)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with barcode '{barcode}' not found in Open Food Facts database."
        )
    return product


MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post(
    "/scan-image",
    response_model=FoodScanResponse,
)
async def scan_food_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
):
    if not ai_rate_limiter.is_allowed(str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Max 10 requests per minute.",
        )
    if file.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}. Allowed: JPEG, PNG, WEBP, GIF.",
        )

    file_bytes = await file.read()

    # Verify actual image content via magic bytes signature
    def is_valid_image(data: bytes) -> bool:
        if len(data) < 12:
            return False
        if data[:3] == b"\xff\xd8\xff":
            return True
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return True
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return True
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return True
        return False

    if not is_valid_image(file_bytes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file format. Content does not match allowed image signatures.",
        )

    if len(file_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image exceeds the 10MB upload limit.",
        )

    service = CalorieService(db, http_client=http_client)
    try:
        filename = file.filename or "image.jpg"
        return await service.scan_image(filename, file_bytes)
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

