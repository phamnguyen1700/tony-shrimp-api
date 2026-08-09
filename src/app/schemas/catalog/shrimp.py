import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.catalog.shrimp import CatalogStatus
from app.schemas.catalog.care_parameter import (
    CareParameterCreate,
    CareParameterResponse,
)
from app.schemas.catalog.shrimp_image import ShrimpImageCreate, ShrimpImageResponse
from app.schemas.catalog.shrimp_variant import (
    ShrimpVariantCreate,
    ShrimpVariantResponse,
)


class ShrimpCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    species: str | None = Field(default=None, max_length=255)
    type: str = Field(min_length=1, max_length=64)
    colors: list[str] = Field(default_factory=list, max_length=10)
    grade: str | None = Field(default=None, max_length=64)
    rarity: str | None = Field(default=None, max_length=64)
    description: str | None = None
    catalog_status: CatalogStatus = CatalogStatus.INACTIVE
    traits: list[str] = Field(default_factory=list)

    variants: list[ShrimpVariantCreate] = Field(default_factory=list)
    care_parameter: CareParameterCreate | None = None
    images: list[ShrimpImageCreate] = Field(default_factory=list, max_length=4)


class ShrimpUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    species: str | None = Field(default=None, max_length=255)
    type: str | None = Field(default=None, min_length=1, max_length=64)
    colors: list[str] | None = Field(default=None, max_length=10)
    grade: str | None = Field(default=None, max_length=64)
    rarity: str | None = Field(default=None, max_length=64)
    description: str | None = None
    catalog_status: CatalogStatus | None = None
    traits: list[str] | None = None


class ShrimpListItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    species: str | None
    type: str
    colors: list[str]
    grade: str | None
    rarity: str | None
    catalog_status: str
    traits: list[str]
    created_at: datetime
    updated_at: datetime
    is_available: bool
    min_price: Decimal | None
    total_stock: int
    primary_image_url: str | None
    care_level: str | None


class ShrimpDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    species: str | None
    type: str
    colors: list[str]
    grade: str | None
    rarity: str | None
    description: str | None
    catalog_status: str
    traits: list[str]
    created_at: datetime
    updated_at: datetime
    is_available: bool
    variants: list[ShrimpVariantResponse]
    care_parameter: CareParameterResponse | None
    images: list[ShrimpImageResponse]
