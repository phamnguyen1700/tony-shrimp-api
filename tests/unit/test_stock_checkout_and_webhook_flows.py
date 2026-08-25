import asyncio
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.catalog import CatalogStatus
from app.models.order import PaymentStatus, StockReservationStatus
from app.schemas.order import CreateOrderItemRequest, CreateOrderRequest
from app.services.order import order_service
from app.services.payment import payment_service


def run_async(coro):
    return asyncio.run(coro)


def make_variant(*, stock_quantity: int, grade: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        is_active=True,
        stock_quantity=stock_quantity,
        price=Decimal("50.00"),
        shrimp=SimpleNamespace(
            catalog_status=CatalogStatus.ACTIVE.value,
            grade=grade,
            name="Red Boa",
            images=[],
        ),
        shrimp_id=uuid.uuid4(),
        name="Pack",
        sale_unit="pack",
        sale_quantity=1,
    )


def make_address() -> SimpleNamespace:
    return SimpleNamespace(
        recipient_name="Tony",
        recipient_phone_encrypted="enc-phone",
        address_line1_encrypted="enc-line1",
        address_line2_encrypted=None,
        suburb="Sydney",
        state="NSW",
        postcode="2000",
    )


def make_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), email="customer@example.com")


class FakeDbSession:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.rollback_calls = 0
        self.refresh_calls = 0

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        self.rollback_calls += 1

    async def refresh(self, _obj) -> None:
        self.refresh_calls += 1


def test_checkout_insufficient_stock_returns_structured_error_and_skips_order_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    address = make_address()
    variant = make_variant(stock_quantity=1)
    create_order_called = False
    stripe_called = False

    async def fake_get_user_address(*args, **kwargs):
        return address

    async def fake_get_variant_for_order(*args, **kwargs):
        return variant

    async def fake_create_order(*args, **kwargs):
        nonlocal create_order_called
        create_order_called = True
        return SimpleNamespace(id=uuid.uuid4(), created_at=datetime.now(UTC))

    def fake_create_checkout_session(*args, **kwargs):
        nonlocal stripe_called
        stripe_called = True
        return {"id": "cs_test", "url": "https://stripe.test/checkout"}

    monkeypatch.setattr(order_service, "get_user_address", fake_get_user_address)
    monkeypatch.setattr(
        order_service, "get_variant_for_order", fake_get_variant_for_order
    )
    monkeypatch.setattr(order_service, "create_order", fake_create_order)
    monkeypatch.setattr(
        order_service,
        "create_order_checkout_session",
        fake_create_checkout_session,
    )

    payload = CreateOrderRequest(
        shipping_address_id=uuid.uuid4(),
        items=[
            CreateOrderItemRequest(
                variant_id=variant.id,
                quantity=2,
            )
        ],
    )

    with pytest.raises(order_service.InsufficientStockCheckoutError) as exc_info:
        run_async(
            order_service.create_customer_order(
                db=SimpleNamespace(),
                current_user=user,
                payload=payload,
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"] == "INSUFFICIENT_STOCK"
    assert exc_info.value.detail["items"] == [
        {
            "variant_id": str(variant.id),
            "requested": 2,
            "available": 1,
        }
    ]
    assert create_order_called is False
    assert stripe_called is False


def test_checkout_multi_item_only_reports_insufficient_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    address = make_address()
    enough_variant = make_variant(stock_quantity=5)
    low_stock_variant = make_variant(stock_quantity=1)

    variants = {
        enough_variant.id: enough_variant,
        low_stock_variant.id: low_stock_variant,
    }

    async def fake_get_user_address(*args, **kwargs):
        return address

    async def fake_get_variant_for_order(_db, variant_id):
        return variants[variant_id]

    monkeypatch.setattr(order_service, "get_user_address", fake_get_user_address)
    monkeypatch.setattr(
        order_service, "get_variant_for_order", fake_get_variant_for_order
    )

    payload = CreateOrderRequest(
        shipping_address_id=uuid.uuid4(),
        items=[
            CreateOrderItemRequest(variant_id=enough_variant.id, quantity=1),
            CreateOrderItemRequest(variant_id=low_stock_variant.id, quantity=3),
        ],
    )

    with pytest.raises(order_service.InsufficientStockCheckoutError) as exc_info:
        run_async(
            order_service.create_customer_order(
                db=SimpleNamespace(),
                current_user=user,
                payload=payload,
            )
        )

    assert exc_info.value.detail["items"] == [
        {
            "variant_id": str(low_stock_variant.id),
            "requested": 3,
            "available": 1,
        }
    ]


def test_checkout_atomic_reservation_failure_returns_409_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeDbSession()
    user = make_user()
    address = make_address()
    variant = make_variant(stock_quantity=1)

    create_order_called = False
    stripe_called = False

    async def fake_get_user_address(*args, **kwargs):
        return address

    async def fake_get_variant_for_order(*args, **kwargs):
        return variant

    async def fake_decrement_variant_stock(_db, *, variant_id, quantity):
        assert variant_id == variant.id
        assert quantity == 1
        variant.stock_quantity = 0
        return False

    async def fake_create_order(*args, **kwargs):
        nonlocal create_order_called
        create_order_called = True
        return SimpleNamespace(id=uuid.uuid4(), created_at=datetime.now(UTC))

    def fake_create_checkout_session(*args, **kwargs):
        nonlocal stripe_called
        stripe_called = True
        return {"id": "cs_test", "url": "https://stripe.test/checkout"}

    monkeypatch.setattr(order_service, "get_user_address", fake_get_user_address)
    monkeypatch.setattr(
        order_service, "get_variant_for_order", fake_get_variant_for_order
    )
    monkeypatch.setattr(
        order_service,
        "decrement_variant_stock",
        fake_decrement_variant_stock,
    )
    monkeypatch.setattr(order_service, "create_order", fake_create_order)
    monkeypatch.setattr(
        order_service,
        "create_order_checkout_session",
        fake_create_checkout_session,
    )

    payload = CreateOrderRequest(
        shipping_address_id=uuid.uuid4(),
        items=[CreateOrderItemRequest(variant_id=variant.id, quantity=1)],
    )

    with pytest.raises(order_service.InsufficientStockCheckoutError) as exc_info:
        run_async(
            order_service.create_customer_order(
                db=db,
                current_user=user,
                payload=payload,
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == {
        "error": "INSUFFICIENT_STOCK",
        "items": [
            {
                "variant_id": str(variant.id),
                "requested": 1,
                "available": 0,
            }
        ],
    }
    assert db.rollback_calls == 1
    assert create_order_called is False
    assert stripe_called is False


def test_checkout_rejects_high_quality_variant_before_order_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    address = make_address()
    variant = make_variant(stock_quantity=5, grade="SSS")
    create_order_called = False
    stripe_called = False
    decrement_called = False

    async def fake_get_user_address(*args, **kwargs):
        return address

    async def fake_get_variant_for_order(*args, **kwargs):
        return variant

    async def fake_decrement_variant_stock(*args, **kwargs):
        nonlocal decrement_called
        decrement_called = True
        return True

    async def fake_create_order(*args, **kwargs):
        nonlocal create_order_called
        create_order_called = True
        return SimpleNamespace(id=uuid.uuid4(), created_at=datetime.now(UTC))

    def fake_create_checkout_session(*args, **kwargs):
        nonlocal stripe_called
        stripe_called = True
        return {"id": "cs_test", "url": "https://stripe.test/checkout"}

    monkeypatch.setattr(order_service, "get_user_address", fake_get_user_address)
    monkeypatch.setattr(
        order_service, "get_variant_for_order", fake_get_variant_for_order
    )
    monkeypatch.setattr(
        order_service,
        "decrement_variant_stock",
        fake_decrement_variant_stock,
    )
    monkeypatch.setattr(order_service, "create_order", fake_create_order)
    monkeypatch.setattr(
        order_service,
        "create_order_checkout_session",
        fake_create_checkout_session,
    )

    payload = CreateOrderRequest(
        shipping_address_id=uuid.uuid4(),
        items=[CreateOrderItemRequest(variant_id=variant.id, quantity=1)],
    )

    with pytest.raises(order_service.ContactOnlyCheckoutError) as exc_info:
        run_async(
            order_service.create_customer_order(
                db=SimpleNamespace(),
                current_user=user,
                payload=payload,
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == {
        "error": "CONTACT_ONLY_ITEM",
        "message": "Please contact us for high quality product.",
        "items": [
            {
                "variant_id": str(variant.id),
                "grade": "SSS",
            }
        ],
    }
    assert decrement_called is False
    assert create_order_called is False
    assert stripe_called is False


def test_webhook_completed_consumes_reservation_once_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeDbSession()
    order = SimpleNamespace(
        id=uuid.uuid4(),
        order_number="TS-123456",
        status="processing",
        payment_status=PaymentStatus.PENDING.value,
        stock_reservation_status=StockReservationStatus.RESERVED.value,
        items=[SimpleNamespace(variant_id=uuid.uuid4(), quantity=1)],
    )

    payment_events: dict[str, SimpleNamespace] = {}
    consume_calls = 0
    status_event_calls = 0
    notify_calls = 0

    async def fake_get_event_for_update(_db, provider_event_id: str):
        return payment_events.get(provider_event_id)

    async def fake_create_payment_event(
        _db,
        *,
        provider,
        provider_event_id,
        event_type,
        payload,
        order_id,
    ):
        event = SimpleNamespace(
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            payload=payload,
            order_id=order_id,
            processed_at=None,
        )
        payment_events[provider_event_id] = event
        return event

    async def fake_mark_processed(_db, payment_event):
        payment_event.processed_at = datetime.now(UTC)
        return payment_event

    async def fake_find_order_for_checkout_session(_db, _stripe_session):
        return order

    async def fake_consume_stock_reservation_once(_db, *, order_id):
        nonlocal consume_calls
        consume_calls += 1
        assert order_id == order.id
        order.stock_reservation_status = StockReservationStatus.CONSUMED.value
        return True

    async def fake_update_order_payment_fields(_db, _order, **kwargs):
        order.payment_status = kwargs["payment_status"]
        return order

    async def fake_create_order_status_event(*args, **kwargs):
        nonlocal status_event_calls
        status_event_calls += 1
        return SimpleNamespace(id=uuid.uuid4())

    async def fake_notify_paid_order(*args, **kwargs):
        nonlocal notify_calls
        notify_calls += 1

    monkeypatch.setattr(
        payment_service,
        "get_payment_event_by_provider_event_id_for_update",
        fake_get_event_for_update,
    )
    monkeypatch.setattr(
        payment_service, "create_payment_event", fake_create_payment_event
    )
    monkeypatch.setattr(
        payment_service, "mark_payment_event_processed", fake_mark_processed
    )
    monkeypatch.setattr(
        payment_service,
        "find_order_for_checkout_session",
        fake_find_order_for_checkout_session,
    )
    monkeypatch.setattr(
        payment_service,
        "consume_stock_reservation_once",
        fake_consume_stock_reservation_once,
    )
    monkeypatch.setattr(
        payment_service,
        "update_order_payment_fields",
        fake_update_order_payment_fields,
    )
    monkeypatch.setattr(
        payment_service,
        "create_order_status_event",
        fake_create_order_status_event,
    )
    monkeypatch.setattr(payment_service, "notify_paid_order", fake_notify_paid_order)

    event = {
        "id": "evt_test_completed",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "payment_intent": "pi_test_123",
                "metadata": {"order_id": str(order.id)},
            }
        },
    }

    run_async(payment_service.handle_stripe_webhook_event(db, event))
    run_async(payment_service.handle_stripe_webhook_event(db, event))

    assert order.payment_status == PaymentStatus.PAID.value
    assert order.stock_reservation_status == StockReservationStatus.CONSUMED.value
    assert consume_calls == 1
    assert status_event_calls == 1
    assert notify_calls == 1
    assert db.commit_calls == 1


def test_release_stock_reservation_is_idempotent_and_restocks_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeDbSession()
    variant_id = uuid.uuid4()
    order = SimpleNamespace(
        id=uuid.uuid4(),
        stock_reservation_status=StockReservationStatus.RESERVED.value,
        items=[SimpleNamespace(variant_id=variant_id, quantity=2)],
    )

    release_calls = 0
    increment_calls = 0
    stock_state = {variant_id: 0}

    async def fake_release_stock_reservation_once(_db, *, order_id):
        nonlocal release_calls
        release_calls += 1
        assert order_id == order.id

        if order.stock_reservation_status != StockReservationStatus.RESERVED.value:
            return False

        order.stock_reservation_status = StockReservationStatus.RELEASED.value
        return True

    async def fake_increment_variant_stock(_db, *, variant_id, quantity):
        nonlocal increment_calls
        increment_calls += 1
        stock_state[variant_id] += quantity
        return True

    monkeypatch.setattr(
        order_service,
        "release_stock_reservation_once",
        fake_release_stock_reservation_once,
    )
    monkeypatch.setattr(
        order_service,
        "increment_variant_stock",
        fake_increment_variant_stock,
    )

    first = run_async(order_service.release_order_stock_reservation(db, order))
    second = run_async(order_service.release_order_stock_reservation(db, order))

    assert first is True
    assert second is False
    assert release_calls == 2
    assert increment_calls == 1
    assert stock_state[variant_id] == 2
    assert order.stock_reservation_status == StockReservationStatus.RELEASED.value
