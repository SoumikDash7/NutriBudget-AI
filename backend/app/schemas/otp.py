from pydantic import BaseModel, Field


class SendOTPRequest(BaseModel):
    email_or_phone: str = Field(..., description="Email address or Phone number to send OTP to")
    purpose: str = Field("register", description="Purpose of the OTP (register or reset_password)")


class VerifyOTPRequest(BaseModel):
    email_or_phone: str = Field(..., description="Email address or Phone number")
    otp_code: str = Field(..., min_length=4, max_length=10, description="The 6-digit OTP code")
    purpose: str = Field("register", description="Purpose of the OTP (register or reset_password)")


class VerifyOTPResponse(BaseModel):
    verified: bool
    message: str
