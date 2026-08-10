import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, require_roles
from app.models.auth import User
from app.models.order import OrderStatus
from app.schemas.order import (
    OrderDetailResponse,
    OrderListResponse,
    UpdateOrderStatusRequest,
    UpdateOrderTrackingRequest,
)
from app.services.order import (
    get_owner_order,
    list_owner_orders,
    update_owner_order_status,
    update_owner_order_tracking,
)

router = APIRouter(prefix="/owner/orders", tags=["orders - owner"])


@router.get("", response_model=OrderListResponse)
async def list_order_management_orders(
    order_status: OrderStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_roles("owner", "admin")),
) -> OrderListResponse:
    return await list_owner_orders(
        db,
        status=order_status,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order_management_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_roles("owner", "admin")),
) -> OrderDetailResponse:
    try:
        return await get_owner_order(db, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{order_id}/status", response_model=OrderDetailResponse)
async def update_order_management_order_status(
    order_id: uuid.UUID,
    payload: UpdateOrderStatusRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> OrderDetailResponse:
    try:
        return await update_owner_order_status(
            db,
            actor_id=current_user.id,
            order_id=order_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{order_id}/tracking", response_model=OrderDetailResponse)
async def update_order_management_order_tracking(
    order_id: uuid.UUID,
    payload: UpdateOrderTrackingRequest,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_roles("owner", "admin")),
) -> OrderDetailResponse:
    try:
        return await update_owner_order_tracking(db, order_id=order_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
