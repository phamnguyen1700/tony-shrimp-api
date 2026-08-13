import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.auth.user import User
    from app.models.order.order_item import OrderItem
    from app.models.order.order_status_event import OrderStatusEvent


class OrderStatus(StrEnum):
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentProvider(StrEnum):
    STRIPE = "stripe"


class CancelledReason(StrEnum):
    PAYMENT_TIMEOUT = "payment_timeout"
    PAYMENT_FAILED = "payment_failed"
    OWNER_CANCELLED = "owner_cancelled"
    CUSTOMER_CANCELLED = "customer_cancelled"
    CUSTOMER_REQUEST = "customer_request"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    order_number: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        default=OrderStatus.PROCESSING.value,
    )
    subtotal_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    shipping_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="AUD",
    )
    payment_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PaymentStatus.PENDING.value,
        index=True,
    )
    payment_provider: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PaymentProvider.STRIPE.value,
        index=True,
    )
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
    )
    stripe_checkout_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    stripe_checkout_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    recipient_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    recipient_phone_encrypted: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    address_line1_encrypted: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    address_line2_encrypted: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    suburb: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    postcode: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    customer_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
    shipped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    payment_failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_reason: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    user: Mapped["User"] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )
    status_events: Mapped[list["OrderStatusEvent"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )
