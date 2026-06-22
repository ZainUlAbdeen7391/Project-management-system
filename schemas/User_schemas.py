from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime


def _check_password_bytes(v: str) -> str:
    if len(v.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 bytes")
    return v


class SignupRequest(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=50)
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone_number: str = Field(..., min_length=7, max_length=20) 
    role_id: str | None = None

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _check_password_bytes(v)

    @field_validator("phone_number", mode="before")
    @classmethod
    def strip_phone(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("phone_number cannot be empty")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _check_password_bytes(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password", mode="before")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _check_password_bytes(v)


class RefreshRequest(BaseModel):
    refresh_token: str


class RoleOut(BaseModel):
    role_id: str
    role_name: str
    role_slug: str
    description: str | None = None


class PermissionOut(BaseModel):
    permission_id: str
    module_id: str
    module_name: str
    permission_name: str
    permission_slug: str
    resource: str
    action: str
    description: str | None = None


class TokenResponse(BaseModel):
    success: bool
    message: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    full_name: str
    email: str
    roles: list[RoleOut] = []
    permissions: list[PermissionOut] = []


class UserResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    username: str
    phone_number: str        
    status: str






