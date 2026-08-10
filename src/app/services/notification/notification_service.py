import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.realtime import publish_notification
from app.models.auth import User
from app.models.notification import Notification
from app.repositories.notification import (
    count_notifications,
    count_unread_notifications,
    create_notification,
    get_notification_by_id,
    list_notifications,
    mark_all_role_notifications_read,
    mark_notification_read,
)
from app.schemas.notification import NotificationListResponse, NotificationResponse


def build_notification_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        recipient_user_id=notification.recipient_user_id,
        recipient_role=notification.recipient_role,
        type=notification.type,
        title=notification.title,
        message=notification.message,
        data=notification.data,
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


async def create_notification_for_audience(
    db: AsyncSession,
    *,
    recipient_user_id: uuid.UUID | None = None,
    recipient_role: str | None = None,
    type: str,
    title: str,
    message: str | None = None,
    data: dict[str, Any] | None = None,
) -> Notification:
    return await create_notification(
        db,
        recipient_user_id=recipient_user_id,
        recipient_role=recipient_role,
        type=type,
        title=title,
        message=message,
        data=data,
    )


async def publish_notifications(notifications: list[Notification]) -> None:
    for notification in notifications:
        payload = build_notification_response(notification).model_dump(mode="json")
        await publish_notification(payload)


async def list_owner_notifications(
    db: AsyncSession,
    *,
    current_user: User,
    unread_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> NotificationListResponse:
    notifications = await list_notifications(
        db,
        recipient_user_id=current_user.id,
        recipient_role=current_user.role,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    total = await count_notifications(
        db,
        recipient_user_id=current_user.id,
        recipient_role=current_user.role,
        unread_only=unread_only,
    )
    unread_count = await count_unread_notifications(
        db,
        recipient_user_id=current_user.id,
        recipient_role=current_user.role,
    )

    return NotificationListResponse(
        items=[build_notification_response(notification) for notification in notifications],
        total=total,
        unread_count=unread_count,
        limit=limit,
        offset=offset,
    )


async def mark_owner_notification_read(
    db: AsyncSession,
    *,
    current_user: User,
    notification_id: uuid.UUID,
) -> NotificationResponse:
    notification = await get_notification_by_id(db, notification_id)
    if notification is None:
        raise ValueError("Notification not found.")

    owns_notification = notification.recipient_user_id == current_user.id
    role_notification = notification.recipient_role == current_user.role
    if not owns_notification and not role_notification:
        raise PermissionError("Notification is not visible to current user.")

    notification = await mark_notification_read(db, notification)
    await db.commit()
    await db.refresh(notification)

    return build_notification_response(notification)


async def mark_owner_all_notifications_read(
    db: AsyncSession,
    *,
    current_user: User,
) -> None:
    await mark_all_role_notifications_read(
        db,
        recipient_user_id=current_user.id,
        recipient_role=current_user.role,
    )
    await db.commit()
