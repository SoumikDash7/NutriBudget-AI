from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
    ChangePasswordRequest,
    MessageResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.schemas.otp import (
    SendOTPRequest,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from app.services.auth.register_service import RegisterService
from app.services.auth.login_service import LoginService
from app.services.auth.token_service import TokenService
from app.services.auth.password_service import PasswordService
from app.services.otp_service import OTPService
from app.core.rate_limit import InMemoryRateLimiter


auth_rate_limiter = InMemoryRateLimiter(requests_limit=10, window_seconds=60)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    if not auth_rate_limiter.is_allowed(f"register:{client_ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again in a minute.",
        )
    service = RegisterService(db)

    try:
        return await service.register(
            email=body.email,
            phone=body.phone,
            password=body.password,
            otp_code=body.otp_code,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=LoginResponse,
)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    if not auth_rate_limiter.is_allowed(f"login:{client_ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again in a minute.",
        )
    service = LoginService(db)

    try:
        return await service.login(
            email=body.email,
            phone=body.phone,
            password=body.password,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
async def refresh(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    service = TokenService(db)

    try:
        return await service.refresh_token(
            request.refresh_token
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.patch(
    "/change-password",
    response_model=MessageResponse,
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PasswordService(db)

    return await service.change_password(
        user=current_user,
        current_password=request.current_password,
        new_password=request.new_password,
    )


@router.post(
    "/send-otp",
    response_model=MessageResponse,
)
async def send_otp(
    request: Request,
    body: SendOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    if not auth_rate_limiter.is_allowed(f"send-otp:{client_ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please try again in a minute.",
        )
    service = OTPService(db)
    try:
        otp_code = await service.generate_and_send_otp(
            email_or_phone=body.email_or_phone,
            purpose=body.purpose,
        )
        message = f"OTP successfully sent to {body.email_or_phone}."
        if settings.APP_ENV == "development":
            message += f" OTP is {otp_code} (in development mode)."
        return {"message": message}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/verify-otp",
    response_model=VerifyOTPResponse,
)
async def verify_otp(
    request: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    service = OTPService(db)
    verified = await service.verify_otp(
        email_or_phone=request.email_or_phone,
        otp_code=request.otp_code,
        purpose=request.purpose,
    )
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code."
        )
    return {
        "verified": True,
        "message": "OTP verified successfully."
    }


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
)
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    if not auth_rate_limiter.is_allowed(f"forgot:{client_ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset attempts. Please try again in a minute.",
        )
    service = PasswordService(db)
    try:
        res = await service.forgot_password(
            email_or_phone=body.email_or_phone
        )
        if "otp_code" in res:
            res["message"] += f" OTP is {res['otp_code']} (in development mode)."
            del res["otp_code"]
        return res
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    service = PasswordService(db)
    try:
        return await service.reset_password(
            email_or_phone=request.email_or_phone,
            otp_code=request.otp_code,
            new_password=request.new_password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/account",
    response_model=MessageResponse,
)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import delete
    from app.models.profile import Profile
    from app.models.calorie import CalorieLog
    from app.models.budget import BudgetTransaction, BudgetNotification, Collaboration

    try:
        # Cascade delete user data to avoid foreign key constraint errors
        await db.execute(delete(Profile).where(Profile.user_id == current_user.id))
        await db.execute(delete(CalorieLog).where(CalorieLog.user_id == current_user.id))
        await db.execute(delete(BudgetTransaction).where(BudgetTransaction.user_id == current_user.id))
        await db.execute(delete(BudgetNotification).where(BudgetNotification.user_id == current_user.id))
        await db.execute(delete(Collaboration).where((Collaboration.owner_id == current_user.id) | (Collaboration.partner_id == current_user.id)))

        # Delete main user record
        await db.delete(current_user)
        await db.commit()
        return {"message": "Your account has been deleted permanently."}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )