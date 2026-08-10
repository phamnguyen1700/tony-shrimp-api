import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class OtpRequest(BaseModel):
    email: EmailStr


class OtpResponse(BaseModel):
    message: str


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class AuthUserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: str
    status: str
    created_at: datetime
    updated_at: datetime


class AuthResponse(BaseModel):
    user: AuthUserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = None


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
