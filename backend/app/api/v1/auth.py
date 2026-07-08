from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

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
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    service = RegisterService(db)

    try:
        return await service.register(
            email=request.email,
            phone=request.phone,
            password=request.password,
            otp_code=request.otp_code,
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
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    service = LoginService(db)

    try:
        return await service.login(
            email=request.email,
            phone=request.phone,
            password=request.password,
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
    request: SendOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    service = OTPService(db)
    try:
        otp_code = await service.generate_and_send_otp(
            email_or_phone=request.email_or_phone,
            purpose=request.purpose,
        )
        return {
            "message": f"OTP successfully sent to {request.email_or_phone}. OTP is {otp_code} (in development mode)."
        }
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
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    service = PasswordService(db)
    try:
        res = await service.forgot_password(
            email_or_phone=request.email_or_phone
        )
        res["message"] += f" OTP is {res['otp_code']} (in development mode)."
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