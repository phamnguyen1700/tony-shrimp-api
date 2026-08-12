import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import PaymentEvent


async def get_payment_event_by_provider_event_id(
    db: AsyncSession,
    provider_event_id: str,
) -> PaymentEvent | None:
    result = await db.execute(
        select(PaymentEvent).where(
            PaymentEvent.provider_event_id == provider_event_id,
        )
    )
    return result.scalar_one_or_none()


async def create_payment_event(
    db: AsyncSession,
    *,
    provider: str,
    provider_event_id: str,
    event_type: str,
    payload: dict[str, Any],
    order_id: uuid.UUID | None = None,
) -> PaymentEvent:
    payment_event = PaymentEvent(
        provider=provider,
        provider_event_id=provider_event_id,
        event_type=event_type,
        order_id=order_id,
        payload=payload,
    )
    db.add(payment_event)
    await db.flush()
    return payment_event


async def mark_payment_event_processed(
    db: AsyncSession,
    payment_event: PaymentEvent,
) -> PaymentEvent:
    payment_event.processed_at = datetime.now(UTC)
    await db.flush()
    return payment_event
