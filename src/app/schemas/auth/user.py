import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: str
    created_at: datetime
    updated_at: datetime
