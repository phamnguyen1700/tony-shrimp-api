import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, require_roles
from app.core.config import get_settings
from app.core.realtime import NOTIFICATIONS_CHANNEL
from app.core.redis import redis_client
from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal
from app.models.auth import User, UserRole, UserStatus
from app.repositories.auth import get_user_by_id
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.notification import (
    list_owner_notifications,
    mark_owner_all_notifications_read,
    mark_owner_notification_read,
)

router = APIRouter(prefix="/owner/notifications", tags=["notifications - owner"])
settings = get_settings()


@router.get("", response_model=NotificationListResponse)
async def list_notifications_for_owner(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> NotificationListResponse:
    return await list_owner_notifications(
        db,
        current_user=current_user,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> NotificationResponse:
    try:
        return await mark_owner_notification_read(
            db,
            current_user=current_user,
            notification_id=notification_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_as_read(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> None:
    await mark_owner_all_notifications_read(db, current_user=current_user)


async def get_websocket_user(token: str | None) -> User | None:
    if token is None:
        return None

    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload["sub"]))
    except Exception:
        return None

    async with AsyncSessionLocal() as db:
        user = await get_user_by_id(db, user_id)
        if user is None or user.status != UserStatus.ACTIVE.value:
            return None
        if user.role not in (UserRole.OWNER.value, UserRole.ADMIN.value):
            return None

        return user


def notification_visible_to_user(payload: dict[str, object], user: User) -> bool:
    return (
        payload.get("recipient_user_id") == str(user.id)
        or payload.get("recipient_role") == user.role
    )


@router.websocket("/ws")
async def owner_notifications_websocket(
    websocket: WebSocket,
) -> None:
    token = websocket.cookies.get(settings.access_token_cookie_name)
    user = await get_websocket_user(token)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(NOTIFICATIONS_CHANNEL)

    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue

            payload = json.loads(str(message["data"]))
            if notification_visible_to_user(payload, user):
                await websocket.send_json(payload)
    finally:
        await pubsub.unsubscribe(NOTIFICATIONS_CHANNEL)
        await pubsub.aclose()
