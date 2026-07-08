from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=10, max_length=15)
    password: str = Field(min_length=8, max_length=128)
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.email and not self.phone:
            raise ValueError("Either email or phone must be provided.")
        return self



class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    phone: str | None
    email_verified: bool
    phone_verified: bool
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse


class LoginRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    password: str

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.email and not self.phone:
            raise ValueError("Either email or phone must be provided.")
        return self


class LoginResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(
        min_length=8,
        max_length=128,
    )


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    email_or_phone: str = Field(..., description="Email or phone to reset password for")


class ResetPasswordRequest(BaseModel):
    email_or_phone: str
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=128)