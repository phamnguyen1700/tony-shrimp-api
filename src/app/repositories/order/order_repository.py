import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth import User
from app.models.catalog import Shrimp, ShrimpVariant
from app.models.order import Order, OrderItem, OrderStatusEvent, StockReservationStatus


async def get_variant_for_order(
    db: AsyncSession,
    variant_id: uuid.UUID,
) -> ShrimpVariant | None:
    result = await db.execute(
        select(ShrimpVariant)
        .options(
            selectinload(ShrimpVariant.shrimp).selectinload(Shrimp.images),
        )
        .where(ShrimpVariant.id == variant_id)
    )
    return result.scalar_one_or_none()


async def create_order(
    db: AsyncSession,
    *,
    order_number: str,
    user_id: uuid.UUID,
    status: str,
    subtotal_amount: Decimal,
    shipping_amount: Decimal,
    total_amount: Decimal,
    currency: str,
    recipient_name: str,
    recipient_phone_encrypted: str,
    address_line1_encrypted: str,
    address_line2_encrypted: str | None,
    suburb: str,
    state: str,
    postcode: str,
    customer_note: str | None,
    payment_status: str | None = None,
    payment_provider: str | None = None,
) -> Order:
    values = dict(
        order_number=order_number,
        user_id=user_id,
        status=status,
        subtotal_amount=subtotal_amount,
        shipping_amount=shipping_amount,
        total_amount=total_amount,
        currency=currency,
        recipient_name=recipient_name,
        recipient_phone_encrypted=recipient_phone_encrypted,
        address_line1_encrypted=address_line1_encrypted,
        address_line2_encrypted=address_line2_encrypted,
        suburb=suburb,
        state=state,
        postcode=postcode,
        customer_note=customer_note,
    )
    if payment_status is not None:
        values["payment_status"] = payment_status
    if payment_provider is not None:
        values["payment_provider"] = payment_provider

    order = Order(**values)
    db.add(order)
    await db.flush()
    return order


async def create_order_item(
    db: AsyncSession,
    *,
    order_id: uuid.UUID,
    shrimp_id: uuid.UUID | None,
    variant_id: uuid.UUID | None,
    shrimp_name_snapshot: str,
    variant_name_snapshot: str,
    sale_unit_snapshot: str,
    sale_quantity_snapshot: int,
    image_url_snapshot: str | None,
    unit_price: Decimal,
    quantity: int,
    line_total: Decimal,
) -> OrderItem:
    item = OrderItem(
        order_id=order_id,
        shrimp_id=shrimp_id,
        variant_id=variant_id,
        shrimp_name_snapshot=shrimp_name_snapshot,
        variant_name_snapshot=variant_name_snapshot,
        sale_unit_snapshot=sale_unit_snapshot,
        sale_quantity_snapshot=sale_quantity_snapshot,
        image_url_snapshot=image_url_snapshot,
        unit_price=unit_price,
        quantity=quantity,
        line_total=line_total,
    )
    db.add(item)
    await db.flush()
    return item


async def create_order_status_event(
    db: AsyncSession,
    *,
    order_id: uuid.UUID,
    status: str,
    message: str | None,
    created_by_user_id: uuid.UUID | None,
    created_at: datetime | None = None,
) -> OrderStatusEvent:
    values = {
        "order_id": order_id,
        "status": status,
        "message": message,
        "created_by_user_id": created_by_user_id,
    }
    if created_at is not None:
        values["created_at"] = created_at

    event = OrderStatusEvent(**values)
    db.add(event)
    await db.flush()
    return event


async def get_order_by_id(
    db: AsyncSession,
    order_id: uuid.UUID,
) -> Order | None:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.status_events))
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def get_order_by_order_number(
    db: AsyncSession,
    order_number: str,
) -> Order | None:
    result = await db.execute(select(Order).where(Order.order_number == order_number))
    return result.scalar_one_or_none()


async def get_order_by_stripe_checkout_session_id(
    db: AsyncSession,
    stripe_checkout_session_id: str,
) -> Order | None:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.status_events))
        .where(Order.stripe_checkout_session_id == stripe_checkout_session_id)
    )
    return result.scalar_one_or_none()


async def get_order_by_stripe_payment_intent_id(
    db: AsyncSession,
    stripe_payment_intent_id: str,
) -> Order | None:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.status_events))
        .where(Order.stripe_payment_intent_id == stripe_payment_intent_id)
    )
    return result.scalar_one_or_none()


async def update_order_payment_fields(
    db: AsyncSession,
    order: Order,
    *,
    payment_status: str | None = None,
    stripe_checkout_session_id: str | None = None,
    stripe_checkout_url: str | None = None,
    stripe_checkout_expires_at: datetime | None = None,
    stripe_payment_intent_id: str | None = None,
    paid_at: datetime | None = None,
    payment_failed_at: datetime | None = None,
    cancelled_reason: str | None = None,
) -> Order:
    if payment_status is not None:
        order.payment_status = payment_status
    if stripe_checkout_session_id is not None:
        order.stripe_checkout_session_id = stripe_checkout_session_id
    if stripe_checkout_url is not None:
        order.stripe_checkout_url = stripe_checkout_url
    if stripe_checkout_expires_at is not None:
        order.stripe_checkout_expires_at = stripe_checkout_expires_at
    if stripe_payment_intent_id is not None:
        order.stripe_payment_intent_id = stripe_payment_intent_id
    if paid_at is not None:
        order.paid_at = paid_at
    if payment_failed_at is not None:
        order.payment_failed_at = payment_failed_at
    if cancelled_reason is not None:
        order.cancelled_reason = cancelled_reason

    await db.flush()
    return order


async def decrement_variant_stock(
    db: AsyncSession,
    *,
    variant_id: uuid.UUID,
    quantity: int,
) -> bool:
    result = await db.execute(
        update(ShrimpVariant)
        .where(
            ShrimpVariant.id == variant_id,
            ShrimpVariant.stock_quantity >= quantity,
        )
        .values(stock_quantity=ShrimpVariant.stock_quantity - quantity)
    )
    await db.flush()
    return bool((result.rowcount or 0) > 0)


async def increment_variant_stock(
    db: AsyncSession,
    *,
    variant_id: uuid.UUID,
    quantity: int,
) -> bool:
    result = await db.execute(
        update(ShrimpVariant)
        .where(ShrimpVariant.id == variant_id)
        .values(stock_quantity=ShrimpVariant.stock_quantity + quantity)
    )
    await db.flush()
    return bool((result.rowcount or 0) > 0)


async def release_stock_reservation_once(
    db: AsyncSession,
    *,
    order_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        update(Order)
        .where(
            Order.id == order_id,
            Order.stock_reservation_status == StockReservationStatus.RESERVED.value,
        )
        .values(stock_reservation_status=StockReservationStatus.RELEASED.value)
    )
    await db.flush()
    return bool((result.rowcount or 0) > 0)


async def consume_stock_reservation_once(
    db: AsyncSession,
    *,
    order_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        update(Order)
        .where(
            Order.id == order_id,
            Order.stock_reservation_status == StockReservationStatus.RESERVED.value,
        )
        .values(stock_reservation_status=StockReservationStatus.CONSUMED.value)
    )
    await db.flush()
    return bool((result.rowcount or 0) > 0)


async def list_pending_payment_orders_older_than(
    db: AsyncSession,
    *,
    minutes: int,
) -> list[Order]:
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    result = await db.execute(
        select(Order).where(
            Order.payment_status == "pending",
            Order.created_at <= cutoff,
        )
    )
    return list(result.scalars().all())


def build_order_filters(
    *,
    user_id: uuid.UUID | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[object]:
    filters: list[object] = []

    if user_id is not None:
        filters.append(Order.user_id == user_id)
    if status:
        filters.append(Order.status == status)
    if search:
        pattern = f"%{search.strip().lower()}%"
        filters.append(
            or_(
                func.lower(Order.order_number).like(pattern),
                func.lower(User.email).like(pattern),
            )
        )

    return filters


async def list_orders(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Order]:
    filters = build_order_filters(user_id=user_id, status=status, search=search)
    query = select(Order).options(selectinload(Order.items))
    if search:
        query = query.join(User)

    result = await db.execute(
        query.where(*filters)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def count_orders(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    status: str | None = None,
    search: str | None = None,
) -> int:
    filters = build_order_filters(user_id=user_id, status=status, search=search)
    query = select(func.count()).select_from(Order)
    if search:
        query = query.join(User)

    result = await db.execute(query.where(*filters))
    return int(result.scalar_one())
