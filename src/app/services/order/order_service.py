import secrets
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.pii import decrypt_pii
from app.models.auth import UserRole
from app.models.catalog import CatalogStatus, ShrimpImage, ShrimpVariant
from app.models.notification import NotificationType
from app.models.order import Order, OrderStatus
from app.repositories.order import (
    count_orders,
    create_order,
    create_order_item,
    create_order_status_event,
    get_order_by_id,
    get_order_by_order_number,
    get_variant_for_order,
    list_orders,
)
from app.repositories.user import get_user_address
from app.schemas.order import (
    CreateOrderRequest,
    OrderAddressResponse,
    OrderDetailResponse,
    OrderItemResponse,
    OrderListResponse,
    OrderResponse,
    OrderStatusEventResponse,
    UpdateOrderStatusRequest,
    UpdateOrderTrackingRequest,
)
from app.services.notification.notification_service import (
    create_notification_for_audience,
    publish_notifications,
)

settings = get_settings()


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
        subtotal_amount=order.subtotal_amount,
        shipping_amount=order.shipping_amount,
        total_amount=order.total_amount,
        currency=order.currency,
        customer_note=order.customer_note,
        carrier=order.carrier,
        tracking_number=order.tracking_number,
        tracking_url=order.tracking_url,
        created_at=order.created_at,
        updated_at=order.updated_at,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at,
        cancelled_at=order.cancelled_at,
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


async def create_customer_order(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: CreateOrderRequest,
) -> OrderDetailResponse:
    address = await get_user_address(
        db,
        user_id=user_id,
        address_id=payload.shipping_address_id,
    )
    if address is None:
        raise ValueError("Shipping address not found.")

    quantities = aggregate_order_items(payload)
    variant_snapshots: list[tuple[ShrimpVariant, int, Decimal]] = []
    subtotal = Decimal("0.00")

    for variant_id, quantity in quantities.items():
        variant = await get_variant_for_order(db, variant_id)
        if variant is None or not variant.is_active:
            raise ValueError("One or more variants are unavailable.")
        if variant.shrimp.catalog_status != CatalogStatus.ACTIVE.value:
            raise ValueError("One or more shrimp are unavailable.")

        line_total = variant.price * quantity
        subtotal += line_total
        variant_snapshots.append((variant, quantity, line_total))

    shipping_amount = settings.order_shipping_flat_rate_amount
    total = subtotal + shipping_amount
    order_number = await create_unique_order_number(db)

    order = await create_order(
        db,
        order_number=order_number,
        user_id=user_id,
        status=OrderStatus.PROCESSING.value,
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
        message="Order received.",
        created_by_user_id=user_id,
        created_at=order.created_at,
    )

    notifications = []
    for role in (UserRole.OWNER.value, UserRole.ADMIN.value):
        notifications.append(
            await create_notification_for_audience(
                db,
                recipient_role=role,
                type=NotificationType.NEW_ORDER.value,
                title=f"New order {order.order_number}",
                message="A new COD order has been placed.",
                data={
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                },
            )
        )

    await db.commit()
    await publish_notifications(notifications)

    refreshed_order = await get_order_by_id(db, order.id)
    if refreshed_order is None:
        raise RuntimeError("Created order could not be loaded.")

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


async def update_owner_order_tracking(
    db: AsyncSession,
    *,
    order_id: uuid.UUID,
    payload: UpdateOrderTrackingRequest,
) -> OrderDetailResponse:
    order = await get_order_by_id(db, order_id)
    if order is None:
        raise ValueError("Order not found.")

    if "carrier" in payload.model_fields_set:
        order.carrier = normalize_note(payload.carrier)
    if "tracking_number" in payload.model_fields_set:
        order.tracking_number = normalize_note(payload.tracking_number)
    if "tracking_url" in payload.model_fields_set:
        order.tracking_url = normalize_note(payload.tracking_url)

    await db.commit()
    refreshed_order = await get_order_by_id(db, order.id)
    if refreshed_order is None:
        raise RuntimeError("Updated order could not be loaded.")

    return build_order_detail_response(refreshed_order)
