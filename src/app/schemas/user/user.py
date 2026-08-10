import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserMeResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    full_name: str | None = None
    phone: str | None = None
    created_at: datetime
    updated_at: datetime


class UpdateUserProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
