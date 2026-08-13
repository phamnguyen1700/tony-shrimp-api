import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import UserRole
from app.models.notification import NotificationType
from app.models.order import (
    CancelledReason,
    Order,
    OrderStatus,
    PaymentProvider,
    PaymentStatus,
)
from app.repositories.order import (
    create_order_status_event,
    get_order_by_id,
    get_order_by_stripe_checkout_session_id,
    get_order_by_stripe_payment_intent_id,
    update_order_payment_fields,
)
from app.repositories.payment import (
    create_payment_event,
    get_payment_event_by_provider_event_id,
    mark_payment_event_processed,
)
from app.services.notification import (
    create_notification_for_audience,
    publish_notifications,
)


def stripe_object_to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict_recursive"):
        return value.to_dict_recursive()
    return dict(value)


def stripe_get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)

    return getattr(value, key, default)


def get_stripe_event_object(event: Any) -> Any:
    data = stripe_get(event, "data", {}) or {}
    return stripe_get(data, "object")


def get_stripe_event_id(event: Any) -> str:
    return str(stripe_get(event, "id"))


def get_stripe_event_type(event: Any) -> str:
    return str(stripe_get(event, "type"))


def get_metadata_order_id(stripe_object: Any) -> uuid.UUID | None:
    metadata = stripe_get(stripe_object, "metadata", {}) or {}
    order_id = stripe_get(metadata, "order_id")

    if not order_id:
        return None

    try:
        return uuid.UUID(str(order_id))
    except ValueError:
        return None


async def notify_paid_order(db: AsyncSession, order: Order) -> None:
    notifications = []
    for role in (UserRole.OWNER.value, UserRole.ADMIN.value):
        notifications.append(
            await create_notification_for_audience(
                db,
                recipient_role=role,
                type=NotificationType.NEW_ORDER.value,
                title=f"Paid order {order.order_number}",
                message="A new paid order is ready to process.",
                data={
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                },
            )
        )

    await publish_notifications(notifications)


async def find_order_for_checkout_session(
    db: AsyncSession,
    stripe_session: Any,
) -> Order | None:
    order_id = get_metadata_order_id(stripe_session)
    if order_id is not None:
        return await get_order_by_id(db, order_id)

    session_id = stripe_get(stripe_session, "id")
    if session_id:
        return await get_order_by_stripe_checkout_session_id(db, str(session_id))

    return None


async def handle_checkout_completed(
    db: AsyncSession,
    stripe_session: Any,
) -> Order | None:
    order = await find_order_for_checkout_session(db, stripe_session)
    if order is None:
        return None

    session_id = stripe_get(stripe_session, "id")
    if not session_id:
        return None

    payment_intent_id = stripe_get(stripe_session, "payment_intent")
    await update_order_payment_fields(
        db,
        order,
        payment_status=PaymentStatus.PAID.value,
        stripe_checkout_session_id=str(session_id),
        stripe_payment_intent_id=str(payment_intent_id) if payment_intent_id else None,
        paid_at=datetime.now(UTC),
    )
    await create_order_status_event(
        db,
        order_id=order.id,
        status=OrderStatus.PROCESSING.value,
        message="Payment received.",
        created_by_user_id=None,
    )
    await notify_paid_order(db, order)
    return order


async def cancel_order_for_failed_payment(
    db: AsyncSession,
    order: Order,
    *,
    reason: CancelledReason,
    message: str,
) -> Order:
    order.status = OrderStatus.CANCELLED.value
    order.cancelled_at = datetime.now(UTC)
    await update_order_payment_fields(
        db,
        order,
        payment_status=PaymentStatus.FAILED.value,
        payment_failed_at=order.cancelled_at,
        cancelled_reason=reason.value,
    )
    await create_order_status_event(
        db,
        order_id=order.id,
        status=OrderStatus.CANCELLED.value,
        message=message,
        created_by_user_id=None,
        created_at=order.cancelled_at,
    )
    return order


async def handle_checkout_expired(
    db: AsyncSession,
    stripe_session: Any,
) -> Order | None:
    order = await find_order_for_checkout_session(db, stripe_session)
    if order is None or order.payment_status != PaymentStatus.PENDING.value:
        return order

    return await cancel_order_for_failed_payment(
        db,
        order,
        reason=CancelledReason.PAYMENT_TIMEOUT,
        message="Payment session expired.",
    )


async def handle_payment_intent_failed(
    db: AsyncSession,
    payment_intent: Any,
) -> Order | None:
    payment_intent_id = stripe_get(payment_intent, "id")
    if not payment_intent_id:
        return None

    order = await get_order_by_stripe_payment_intent_id(db, payment_intent_id)
    if order is None:
        order_id = get_metadata_order_id(payment_intent)
        order = await get_order_by_id(db, order_id) if order_id is not None else None
    if order is None or order.payment_status != PaymentStatus.PENDING.value:
        return order

    return await cancel_order_for_failed_payment(
        db,
        order,
        reason=CancelledReason.PAYMENT_FAILED,
        message="Payment failed.",
    )


async def handle_charge_refunded(
    db: AsyncSession,
    charge: Any,
) -> Order | None:
    payment_intent_id = stripe_get(charge, "payment_intent")
    if not payment_intent_id:
        return None

    order = await get_order_by_stripe_payment_intent_id(db, str(payment_intent_id))
    if order is None:
        return None

    await update_order_payment_fields(
        db,
        order,
        payment_status=PaymentStatus.REFUNDED.value,
    )
    await create_order_status_event(
        db,
        order_id=order.id,
        status=order.status,
        message="Payment refunded.",
        created_by_user_id=None,
    )
    return order


async def handle_stripe_webhook_event(
    db: AsyncSession,
    event: Any,
) -> None:
    provider_event_id = get_stripe_event_id(event)
    existing_event = await get_payment_event_by_provider_event_id(db, provider_event_id)
    if existing_event is not None and existing_event.processed_at is not None:
        return

    event_type = get_stripe_event_type(event)
    stripe_object = get_stripe_event_object(event)
    order_id = get_metadata_order_id(stripe_object)

    payment_event = existing_event
    if payment_event is None:
        payment_event = await create_payment_event(
            db,
            provider=PaymentProvider.STRIPE.value,
            provider_event_id=provider_event_id,
            event_type=event_type,
            payload=stripe_object_to_dict(event),
            order_id=order_id,
        )

    handled_order = None
    if event_type == "checkout.session.completed":
        handled_order = await handle_checkout_completed(db, stripe_object)
    elif event_type == "checkout.session.expired":
        handled_order = await handle_checkout_expired(db, stripe_object)
    elif event_type == "payment_intent.payment_failed":
        handled_order = await handle_payment_intent_failed(db, stripe_object)
    elif event_type == "charge.refunded":
        handled_order = await handle_charge_refunded(db, stripe_object)

    if handled_order is not None:
        payment_event.order_id = handled_order.id

    await mark_payment_event_processed(db, payment_event)
    await db.commit()
