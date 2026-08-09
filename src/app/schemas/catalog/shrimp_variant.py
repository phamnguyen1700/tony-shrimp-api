import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.catalog.shrimp_variant import SaleUnit


class ShrimpVariantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sale_unit: SaleUnit
    sale_quantity: Literal[1, 5, 10]
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    stock_quantity: int = Field(default=0, ge=0)
    is_active: bool = True


class ShrimpVariantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sale_unit: SaleUnit | None = None
    sale_quantity: Literal[1, 5, 10] | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    stock_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ShrimpVariantResponse(BaseModel):
    id: uuid.UUID
    shrimp_id: uuid.UUID
    name: str
    sale_unit: str
    sale_quantity: int
    price: Decimal
    stock_quantity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @property
    def in_stock(self) -> bool:
        return self.is_active and self.stock_quantity > 0
