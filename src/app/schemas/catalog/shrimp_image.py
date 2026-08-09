import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class ShrimpImageCreate(BaseModel):
    r2_key: str = Field(min_length=1, max_length=500)
    url: HttpUrl | None = None
    alt_text: str | None = None
    sort_order: int = Field(default=0, ge=0)
    is_primary: bool = False


class ShrimpImageUpdate(BaseModel):
    alt_text: str | None = None
    sort_order: int | None = Field(default=None, ge=0)


class ShrimpImageResponse(BaseModel):
    id: uuid.UUID
    shrimp_id: uuid.UUID
    r2_key: str
    url: str | None
    alt_text: str | None
    sort_order: int
    is_primary: bool
    created_at: datetime
