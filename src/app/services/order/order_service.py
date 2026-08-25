import secrets
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.pii import decrypt_pii
from app.models.auth import User
from app.models.catalog import CatalogStatus, ShrimpImage, ShrimpVariant
from app.models.order import (
    CancelledReason,
    Order,
    OrderStatus,
    PaymentProvider,
    PaymentStatus,
    StockReservationStatus,
)
from app.repositories.order import (
    count_orders,
    create_order,
    create_order_item,
    create_order_status_event,
    get_order_by_id,
    get_order_by_order_number,
    get_order_by_stripe_checkout_session_id,
    get_variant_for_order,
    list_orders,
    update_order_payment_fields,
    decrement_variant_stock,
    increment_variant_stock,
    release_stock_reservation_once,
)
from app.repositories.user import get_user_address
from app.schemas.order import (
    CheckoutOrderResponse,
    CreateOrderRequest,
    OrderAddressResponse,
    OrderDetailResponse,
    OrderItemResponse,
    OrderListResponse,
    OrderResponse,
    OrderStatusEventResponse,
    UpdateOrderStatusRequest,
)
from app.services.catalog.premium_policy import (
    HIGH_QUALITY_CONTACT_MESSAGE,
    is_high_quality_grade,
)
from app.services.payment import create_order_checkout_session

settings = get_settings()


class CheckoutDomainError(ValueError):
    def __init__(self, *, status_code: int, detail: object) -> None:
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


class InsufficientStockCheckoutError(CheckoutDomainError):
    def __init__(self, items: list[dict[str, object]]) -> None:
        super().__init__(
            status_code=409,
            detail={
                "error": "INSUFFICIENT_STOCK",
                "items": items,
            },
        )


class ContactOnlyCheckoutError(CheckoutDomainError):
    def __init__(self, items: list[dict[str, object]]) -> None:
        super().__init__(
            status_code=400,
            detail={
                "error": "CONTACT_ONLY_ITEM",
                "message": HIGH_QUALITY_CONTACT_MESSAGE,
                "items": items,
            },
        )


def normalize_note(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def normalize_status_at(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value


def stripe_get(value: object, key: str, default: object = None) -> object:
    if isinstance(value, dict):
        return value.get(key, default)

    return getattr(value, key, default)


def datetime_from_stripe_timestamp(value: object) -> datetime | None:
    if value is None:
        return None

    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError):
        return None


async def create_unique_order_number(db: AsyncSession) -> str:
    for _ in range(10):
        candidate = f"TS-{secrets.randbelow(900000) + 100000}"
        existing = await get_order_by_order_number(db, candidate)
        if existing is None:
            return candidate

    raise RuntimeError("Could not generate unique order number.")


def get_primary_image_url(variant: ShrimpVariant) -> str | None:
    images = sorted(
        variant.shrimp.images,
        key=lambda image: (image.sort_order, image.created_at),
    )
    if not images:
        return None

    return images[0].url


def build_order_address_response(order: Order) -> OrderAddressResponse:
    return OrderAddressResponse(
        recipient_name=order.recipient_name,
        recipient_phone=decrypt_pii(order.recipient_phone_encrypted) or "",
        address_line1=decrypt_pii(order.address_line1_encrypted) or "",
        address_line2=decrypt_pii(order.address_line2_encrypted),
        suburb=order.suburb,
        state=order.state,
        postcode=order.postcode,
    )


def build_order_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        user_id=order.user_id,
        status=order.status,
        payment_status=order.payment_status,
        payment_provider=order.payment_provider,
        stripe_checkout_url=order.stripe_checkout_url,
        stripe_checkout_expires_at=order.stripe_checkout_expires_at,
        subtotal_amount=order.subtotal_amount,
        shipping_amount=order.shipping_amount,
        total_amount=order.total_amount,
        currency=order.currency,
        customer_note=order.customer_note,
        created_at=order.created_at,
        updated_at=order.updated_at,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at,
        cancelled_at=order.cancelled_at,
        paid_at=order.paid_at,
        payment_failed_at=order.payment_failed_at,
        cancelled_reason=order.cancelled_reason,
    )


def build_order_detail_response(order: Order) -> OrderDetailResponse:
    return OrderDetailResponse(
        **build_order_response(order).model_dump(),
        shipping_address=build_order_address_response(order),
        items=[
            OrderItemResponse(
                id=item.id,
                shrimp_id=item.shrimp_id,
                variant_id=item.variant_id,
                shrimp_name=item.shrimp_name_snapshot,
                variant_name=item.variant_name_snapshot,
                sale_unit=item.sale_unit_snapshot,
                sale_quantity=item.sale_quantity_snapshot,
                image_url=item.image_url_snapshot,
                unit_price=item.unit_price,
                quantity=item.quantity,
                line_total=item.line_total,
                created_at=item.created_at,
            )
            for item in order.items
        ],
        status_events=[
            OrderStatusEventResponse(
                id=event.id,
                status=event.status,
                message=event.message,
                created_by_user_id=event.created_by_user_id,
                created_at=event.created_at,
            )
            for event in sorted(order.status_events, key=lambda event: event.created_at)
        ],
    )


def aggregate_order_items(payload: CreateOrderRequest) -> dict[uuid.UUID, int]:
    quantities: dict[uuid.UUID, int] = {}
    for item in payload.items:
        quantities[item.variant_id] = quantities.get(item.variant_id, 0) + item.quantity

    return quantities


async def release_order_stock_reservation(
    db: AsyncSession,
    order: Order,
) -> bool:
    released = await release_stock_reservation_once(
        db,
        order_id=order.id,
    )

    if not released:
        return False

    for item in order.items:
        if item.variant_id is None:
            continue

        await increment_variant_stock(
            db,
            variant_id=item.variant_id,
            quantity=item.quantity,
        )

    return True


async def create_customer_order(
    db: AsyncSession,
    *,
    current_user: User,
    payload: CreateOrderRequest,
) -> CheckoutOrderResponse:
    address = await get_user_address(
        db,
        user_id=current_user.id,
        address_id=payload.shipping_address_id,
    )
    if address is None:
        raise ValueError("Shipping address not found.")

    quantities = aggregate_order_items(payload)
    variant_snapshots: list[tuple[ShrimpVariant, int, Decimal]] = []
    subtotal = Decimal("0.00")

    insufficient_stock_items: list[dict[str, object]] = []
    contact_only_items: list[dict[str, object]] = []
    for variant_id, quantity in quantities.items():
        variant = await get_variant_for_order(db, variant_id)
        if variant is None or not variant.is_active:
            raise ValueError("One or more variants are unavailable.")
        if variant.shrimp.catalog_status != CatalogStatus.ACTIVE.value:
            raise ValueError("One or more shrimp are unavailable.")
        if is_high_quality_grade(variant.shrimp.grade):
            contact_only_items.append(
                {
                    "variant_id": str(variant.id),
                    "grade": variant.shrimp.grade,
                }
            )
            continue
        if variant.stock_quantity < quantity:
            insufficient_stock_items.append(
                {
                    "variant_id": str(variant.id),
                    "requested": quantity,
                    "available": variant.stock_quantity,
                }
            )
            continue

        line_total = variant.price * quantity
        subtotal += line_total
        variant_snapshots.append((variant, quantity, line_total))

    if contact_only_items:
        raise ContactOnlyCheckoutError(contact_only_items)

    if insufficient_stock_items:
        raise InsufficientStockCheckoutError(insufficient_stock_items)

    try:
        reservation_failures: list[dict[str, object]] = []
        for variant, quantity, _ in variant_snapshots:
            reserved = await decrement_variant_stock(
                db, variant_id=variant.id, quantity=quantity
            )

            if reserved:
                continue

            await db.refresh(variant)

            reservation_failures.append(
                {
                    "variant_id": str(variant.id),
                    "requested": quantity,
                    "available": variant.stock_quantity,
                }
            )

        if reservation_failures:
            raise InsufficientStockCheckoutError(reservation_failures)

        shipping_amount = settings.order_shipping_flat_rate_amount
        total = subtotal + shipping_amount
        order_number = await create_unique_order_number(db)

        order = await create_order(
            db,
            order_number=order_number,
            user_id=current_user.id,
            status=OrderStatus.PROCESSING.value,
            payment_status=PaymentStatus.PENDING.value,
            payment_provider=PaymentProvider.STRIPE.value,
            subtotal_amount=subtotal,
            shipping_amount=shipping_amount,
            total_amount=total,
            currency=settings.order_currency,
            recipient_name=address.recipient_name,
            recipient_phone_encrypted=address.recipient_phone_encrypted,
            address_line1_encrypted=address.address_line1_encrypted,
            address_line2_encrypted=address.address_line2_encrypted,
            suburb=address.suburb,
            state=address.state,
            postcode=address.postcode,
            customer_note=normalize_note(payload.customer_note),
        )

        for variant, quantity, line_total in variant_snapshots:
            await create_order_item(
                db,
                order_id=order.id,
                shrimp_id=variant.shrimp_id,
                variant_id=variant.id,
                shrimp_name_snapshot=variant.shrimp.name,
                variant_name_snapshot=variant.name,
                sale_unit_snapshot=variant.sale_unit,
                sale_quantity_snapshot=variant.sale_quantity,
                image_url_snapshot=get_primary_image_url(variant),
                unit_price=variant.price,
                quantity=quantity,
                line_total=line_total,
            )

        await create_order_status_event(
            db,
            order_id=order.id,
            status=OrderStatus.PROCESSING.value,
            message="Checkout created.",
            created_by_user_id=current_user.id,
            created_at=order.created_at,
        )

        refreshed_order = await get_order_by_id(db, order.id)
        if refreshed_order is None:
            raise RuntimeError("Created order could not be loaded.")

        checkout_session = create_order_checkout_session(
            order=refreshed_order,
            customer_email=current_user.email,
        )
        checkout_url = stripe_get(checkout_session, "url")
        if not checkout_url:
            raise RuntimeError("Stripe checkout session did not return a URL.")

        checkout_session_id = stripe_get(checkout_session, "id")
        if not checkout_session_id:
            raise RuntimeError("Stripe checkout session did not return an ID.")
        checkout_expires_at = datetime_from_stripe_timestamp(
            stripe_get(checkout_session, "expires_at")
        )

        await update_order_payment_fields(
            db,
            refreshed_order,
            stripe_checkout_session_id=str(checkout_session_id),
            stripe_checkout_url=str(checkout_url),
            stripe_checkout_expires_at=checkout_expires_at,
        )
        await db.commit()

    except Exception:
        await db.rollback()
        raise

    created = await get_order_by_id(db, order.id)
    if created is None:
        raise RuntimeError("Created order could not be loaded.")

    return CheckoutOrderResponse(
        order=build_order_detail_response(created),
        checkout_url=str(checkout_url),
        stripe_session_id=str(checkout_session_id),
        stripe_checkout_expires_at=checkout_expires_at,
    )


def order_can_continue_payment(order: Order) -> bool:
    return (
        order.status == OrderStatus.PROCESSING.value
        and order.payment_status == PaymentStatus.PENDING.value
        and order.stock_reservation_status == StockReservationStatus.RESERVED.value
    )


def order_has_active_checkout_url(order: Order) -> bool:
    if not order.stripe_checkout_url or order.stripe_checkout_expires_at is None:
        return False

    return order.stripe_checkout_expires_at > datetime.now(UTC)


async def continue_customer_order_payment(
    db: AsyncSession,
    *,
    current_user: User,
    order_id: uuid.UUID,
) -> CheckoutOrderResponse:
    order = await get_order_by_id(db, order_id)
    if order is None or order.user_id != current_user.id:
        raise ValueError("Order not found.")
    if not order_can_continue_payment(order):
        raise ValueError("Order cannot continue payment.")

    if order_has_active_checkout_url(order):
        return CheckoutOrderResponse(
            order=build_order_detail_response(order),
            checkout_url=str(order.stripe_checkout_url),
            stripe_session_id=str(order.stripe_checkout_session_id or ""),
            stripe_checkout_expires_at=order.stripe_checkout_expires_at,
        )

    checkout_session = create_order_checkout_session(
        order=order,
        customer_email=current_user.email,
    )
    checkout_url = stripe_get(checkout_session, "url")
    if not checkout_url:
        raise RuntimeError("Stripe checkout session did not return a URL.")

    checkout_session_id = stripe_get(checkout_session, "id")
    if not checkout_session_id:
        raise RuntimeError("Stripe checkout session did not return an ID.")
    checkout_expires_at = datetime_from_stripe_timestamp(
        stripe_get(checkout_session, "expires_at")
    )

    await update_order_payment_fields(
        db,
        order,
        stripe_checkout_session_id=str(checkout_session_id),
        stripe_checkout_url=str(checkout_url),
        stripe_checkout_expires_at=checkout_expires_at,
    )
    await db.commit()

    refreshed_order = await get_order_by_id(db, order.id)
    if refreshed_order is None:
        raise RuntimeError("Order could not be loaded.")

    return CheckoutOrderResponse(
        order=build_order_detail_response(refreshed_order),
        checkout_url=str(checkout_url),
        stripe_session_id=str(checkout_session_id),
        stripe_checkout_expires_at=checkout_expires_at,
    )


async def cancel_customer_order(
    db: AsyncSession,
    *,
    current_user: User,
    order_id: uuid.UUID,
) -> OrderDetailResponse:
    order = await get_order_by_id(db, order_id)
    if order is None or order.user_id != current_user.id:
        raise ValueError("Order not found.")
    if not order_can_continue_payment(order):
        raise ValueError("Only pending payment orders can be cancelled.")

    cancelled_at = datetime.now(UTC)

    await release_order_stock_reservation(db, order)

    order.status = OrderStatus.CANCELLED.value
    order.cancelled_at = cancelled_at
    await update_order_payment_fields(
        db,
        order,
        payment_status=PaymentStatus.FAILED.value,
        payment_failed_at=cancelled_at,
        cancelled_reason=CancelledReason.CUSTOMER_CANCELLED.value,
    )
    await create_order_status_event(
        db,
        order_id=order.id,
        status=OrderStatus.CANCELLED.value,
        message="Customer cancelled unpaid order.",
        created_by_user_id=current_user.id,
        created_at=cancelled_at,
    )
    await db.commit()

    refreshed_order = await get_order_by_id(db, order.id)
    if refreshed_order is None:
        raise RuntimeError("Cancelled order could not be loaded.")

    return build_order_detail_response(refreshed_order)


async def list_customer_orders(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> OrderListResponse:
    orders = await list_orders(db, user_id=user_id, limit=limit, offset=offset)
    total = await count_orders(db, user_id=user_id)
    return OrderListResponse(
        items=[build_order_response(order) for order in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_customer_order(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    order_id: uuid.UUID,
) -> OrderDetailResponse:
    order = await get_order_by_id(db, order_id)
    if order is None or order.user_id != user_id:
        raise ValueError("Order not found.")

    return build_order_detail_response(order)


async def get_customer_order_by_payment_session(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    stripe_session_id: str,
) -> OrderDetailResponse:
    order = await get_order_by_stripe_checkout_session_id(db, stripe_session_id)
    if order is None or order.user_id != user_id:
        raise ValueError("Order not found.")

    return build_order_detail_response(order)


async def list_owner_orders(
    db: AsyncSession,
    *,
    status: OrderStatus | None = None,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> OrderListResponse:
    status_value = status.value if status else None
    orders = await list_orders(
        db,
        status=status_value,
        search=search,
        limit=limit,
        offset=offset,
    )
    total = await count_orders(db, status=status_value, search=search)
    return OrderListResponse(
        items=[build_order_response(order) for order in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_owner_order(
    db: AsyncSession,
    order_id: uuid.UUID,
) -> OrderDetailResponse:
    order = await get_order_by_id(db, order_id)
    if order is None:
        raise ValueError("Order not found.")

    return build_order_detail_response(order)


async def update_owner_order_status(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID,
    order_id: uuid.UUID,
    payload: UpdateOrderStatusRequest,
) -> OrderDetailResponse:
    order = await get_order_by_id(db, order_id)
    if order is None:
        raise ValueError("Order not found.")

    order.status = payload.status.value
    status_at = normalize_status_at(payload.status_at)
    if payload.status == OrderStatus.SHIPPED:
        order.shipped_at = status_at
    elif payload.status == OrderStatus.DELIVERED:
        order.delivered_at = status_at
    elif payload.status == OrderStatus.CANCELLED:
        if (
            order.payment_status == PaymentStatus.PENDING.value
            and order.stock_reservation_status == StockReservationStatus.RESERVED.value
        ):
            await release_order_stock_reservation(db, order)

        order.cancelled_at = status_at

    await create_order_status_event(
        db,
        order_id=order.id,
        status=payload.status.value,
        message=normalize_note(payload.message),
        created_by_user_id=actor_id,
        created_at=status_at,
    )

    await db.commit()

    refreshed_order = await get_order_by_id(db, order.id)
    if refreshed_order is None:
        raise RuntimeError("Updated order could not be loaded.")

    return build_order_detail_response(refreshed_order)
