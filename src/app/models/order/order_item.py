import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.order.order import Order


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    shrimp_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shrimp.id", ondelete="SET NULL"),
        nullable=True,
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shrimp_variants.id", ondelete="SET NULL"),
        nullable=True,
    )
    shrimp_name_snapshot: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    variant_name_snapshot: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    sale_unit_snapshot: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    sale_quantity_snapshot: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    image_url_snapshot: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    order: Mapped["Order"] = relationship(back_populates="items")
