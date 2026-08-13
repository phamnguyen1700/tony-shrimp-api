import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.models.auth import User
from app.schemas.order import (
    CheckoutOrderResponse,
    CreateOrderRequest,
    OrderDetailResponse,
    OrderListResponse,
)
from app.services.order import (
    cancel_customer_order,
    continue_customer_order_payment,
    create_customer_order,
    get_customer_order,
    get_customer_order_by_payment_session,
    list_customer_orders,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "/checkout",
    response_model=CheckoutOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order_checkout(
    payload: CreateOrderRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> CheckoutOrderResponse:
    try:
        return await create_customer_order(
            db,
            current_user=current_user,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=OrderListResponse)
async def list_my_orders(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OrderListResponse:
    return await list_customer_orders(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.get("/payment-session/{session_id}", response_model=OrderDetailResponse)
async def get_my_order_by_payment_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OrderDetailResponse:
    try:
        return await get_customer_order_by_payment_session(
            db,
            user_id=current_user.id,
            stripe_session_id=session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_my_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OrderDetailResponse:
    try:
        return await get_customer_order(
            db,
            user_id=current_user.id,
            order_id=order_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{order_id}/continue-payment", response_model=CheckoutOrderResponse)
async def continue_my_order_payment(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> CheckoutOrderResponse:
    try:
        return await continue_customer_order_payment(
            db,
            current_user=current_user,
            order_id=order_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{order_id}/cancel", response_model=OrderDetailResponse)
async def cancel_my_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OrderDetailResponse:
    try:
        return await cancel_customer_order(
            db,
            current_user=current_user,
            order_id=order_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
