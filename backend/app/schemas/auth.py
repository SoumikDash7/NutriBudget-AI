from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator
from uuid import UUID


class RegisterRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=10, max_length=15)
    password: str = Field(min_length=8, max_length=128)

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
    token_type: str


class RegisterResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse