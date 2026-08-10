import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: uuid.UUID
    recipient_user_id: uuid.UUID | None
    recipient_role: str | None
    type: str
    title: str
    message: str | None
    data: dict[str, Any]
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int
    limit: int
    offset: int
