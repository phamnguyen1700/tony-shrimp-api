import uuid

import pytest
from pydantic import ValidationError

from app.models.order import OrderStatus
from app.schemas.order import (
    CreateOrderItemRequest,
    CreateOrderRequest,
    UpdateOrderStatusRequest,
)


def test_create_order_requires_at_least_one_item() -> None:
    with pytest.raises(ValidationError):
        CreateOrderRequest(shipping_address_id=uuid.uuid4(), items=[])


@pytest.mark.parametrize("quantity", [0, 1000])
def test_create_order_item_rejects_quantity_outside_bounds(quantity: int) -> None:
    with pytest.raises(ValidationError):
        CreateOrderItemRequest(variant_id=uuid.uuid4(), quantity=quantity)


def test_create_order_accepts_customer_note() -> None:
    request = CreateOrderRequest(
        shipping_address_id=uuid.uuid4(),
        items=[
            CreateOrderItemRequest(
                variant_id=uuid.uuid4(),
                quantity=2,
            )
        ],
        customer_note="Please call before shipping.",
    )

    assert request.customer_note == "Please call before shipping."


def test_update_order_status_accepts_supported_status() -> None:
    request = UpdateOrderStatusRequest(status=OrderStatus.SHIPPED)

    assert request.status == OrderStatus.SHIPPED

