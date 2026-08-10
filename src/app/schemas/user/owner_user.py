import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.auth import UserRole
from app.schemas.user.address import UserAddressResponse


class OwnerUserListItemResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    status: str
    full_name: str | None = None
    phone: str | None = None
    created_at: datetime
    updated_at: datetime
    deactivated_at: datetime | None = None


class OwnerUserListResponse(BaseModel):
    items: list[OwnerUserListItemResponse]
    total: int
    limit: int
    offset: int


class OwnerUserDetailResponse(OwnerUserListItemResponse):
    addresses: list[UserAddressResponse]


class UpdateUserRoleRequest(BaseModel):
    role: UserRole
