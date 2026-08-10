import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


def build_notification_filters(
    *,
    recipient_user_id: uuid.UUID | None = None,
    recipient_role: str | None = None,
    unread_only: bool = False,
) -> list[object]:
    filters: list[object] = []
    audience_filters: list[object] = []

    if recipient_user_id is not None:
        audience_filters.append(Notification.recipient_user_id == recipient_user_id)
    if recipient_role:
        audience_filters.append(Notification.recipient_role == recipient_role)
    if audience_filters:
        filters.append(or_(*audience_filters))
    if unread_only:
        filters.append(Notification.read_at.is_(None))

    return filters


async def create_notification(
    db: AsyncSession,
    *,
    recipient_user_id: uuid.UUID | None = None,
    recipient_role: str | None = None,
    type: str,
    title: str,
    message: str | None = None,
    data: dict[str, Any] | None = None,
) -> Notification:
    notification = Notification(
        recipient_user_id=recipient_user_id,
        recipient_role=recipient_role,
        type=type,
        title=title,
        message=message,
        data=data or {},
    )
    db.add(notification)
    await db.flush()
    return notification


async def get_notification_by_id(
    db: AsyncSession,
    notification_id: uuid.UUID,
) -> Notification | None:
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    return result.scalar_one_or_none()


async def list_notifications(
    db: AsyncSession,
    *,
    recipient_user_id: uuid.UUID | None = None,
    recipient_role: str | None = None,
    unread_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> list[Notification]:
    filters = build_notification_filters(
        recipient_user_id=recipient_user_id,
        recipient_role=recipient_role,
        unread_only=unread_only,
    )
    result = await db.execute(
        select(Notification)
        .where(*filters)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def count_notifications(
    db: AsyncSession,
    *,
    recipient_user_id: uuid.UUID | None = None,
    recipient_role: str | None = None,
    unread_only: bool = False,
) -> int:
    filters = build_notification_filters(
        recipient_user_id=recipient_user_id,
        recipient_role=recipient_role,
        unread_only=unread_only,
    )
    result = await db.execute(select(func.count()).select_from(Notification).where(*filters))
    return int(result.scalar_one())


async def count_unread_notifications(
    db: AsyncSession,
    *,
    recipient_user_id: uuid.UUID | None = None,
    recipient_role: str | None = None,
) -> int:
    return await count_notifications(
        db,
        recipient_user_id=recipient_user_id,
        recipient_role=recipient_role,
        unread_only=True,
    )


async def mark_notification_read(
    db: AsyncSession,
    notification: Notification,
) -> Notification:
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        await db.flush()
    return notification


async def mark_all_role_notifications_read(
    db: AsyncSession,
    *,
    recipient_user_id: uuid.UUID | None = None,
    recipient_role: str | None = None,
) -> None:
    filters = build_notification_filters(
        recipient_user_id=recipient_user_id,
        recipient_role=recipient_role,
        unread_only=True,
    )
    await db.execute(
        update(Notification).where(*filters).values(read_at=datetime.now(UTC))
    )
