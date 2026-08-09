import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.catalog.shrimp import Shrimp


class SaleUnit(StrEnum):
    EACH = "each"
    PACK = "pack"


class ShrimpVariant(Base):
    __tablename__ = "shrimp_variants"
    __table_args__ = (
        CheckConstraint(
            "sale_quantity IN (1, 5, 10)", name="ck_shrimp_variants_sale_quantity"
        ),
        CheckConstraint("price >= 0", name="ck_shrimp_variants_price_non_negative"),
        CheckConstraint(
            "stock_quantity >= 0", name="ck_shrimp_variants_stock_non_negative"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    shrimp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shrimp.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    sale_unit: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SaleUnit.EACH.value,
    )
    sale_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    shrimp: Mapped["Shrimp"] = relationship(back_populates="variants")
