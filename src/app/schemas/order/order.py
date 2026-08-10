import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.order import OrderStatus


class CreateOrderItemRequest(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(ge=1, le=999)


class CreateOrderRequest(BaseModel):
    shipping_address_id: uuid.UUID
    items: list[CreateOrderItemRequest] = Field(min_length=1)
    customer_note: str | None = Field(default=None, max_length=1000)


class OrderAddressResponse(BaseModel):
    recipient_name: str
    recipient_phone: str
    address_line1: str
    address_line2: str | None
    suburb: str
    state: str
    postcode: str


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    shrimp_id: uuid.UUID | None
    variant_id: uuid.UUID | None
    shrimp_name: str
    variant_name: str
    sale_unit: str
    sale_quantity: int
    image_url: str | None
    unit_price: Decimal
    quantity: int
    line_total: Decimal
    created_at: datetime


class OrderStatusEventResponse(BaseModel):
    id: uuid.UUID
    status: str
    message: str | None
    created_by_user_id: uuid.UUID | None
    created_at: datetime


class OrderResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    user_id: uuid.UUID
    status: str
    subtotal_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    currency: str
    customer_note: str | None
    carrier: str | None
    tracking_number: str | None
    tracking_url: str | None
    created_at: datetime
    updated_at: datetime
    shipped_at: datetime | None
    delivered_at: datetime | None
    cancelled_at: datetime | None


class OrderDetailResponse(OrderResponse):
    shipping_address: OrderAddressResponse
    items: list[OrderItemResponse]
    status_events: list[OrderStatusEventResponse]


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    limit: int
    offset: int


class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus
    message: str | None = Field(default=None, max_length=1000)
    status_at: datetime | None = None


class UpdateOrderTrackingRequest(BaseModel):
    carrier: str | None = Field(default=None, max_length=100)
    tracking_number: str | None = Field(default=None, max_length=100)
    tracking_url: str | None = Field(default=None, max_length=1000)
