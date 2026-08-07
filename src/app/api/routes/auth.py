from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_redis_client, get_current_user
from app.schemas.auth import OtpRequest, OtpResponse, TokenResponse, VerifyOtpRequest
from app.schemas.auth.auth import LogoutRequest, RefreshTokenRequest
from app.services.auth import request_otp, verify_otp_and_create_session

from app.models.auth.user import User
from app.schemas.auth import CurrentUserResponse
from app.services.auth.auth_service import (
    logout_session,
    refresh_access_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/request-otp", response_model=OtpResponse)
async def request_login_otp(
    payload: OtpRequest,
    redis: Redis = Depends(get_redis_client),
) -> OtpResponse:
    try:
        return await request_otp(redis, str(payload.email))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_login_otp(
    payload: VerifyOtpRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
) -> TokenResponse:
    try:
        return await verify_otp_and_create_session(
            db,
            redis,
            email=str(payload.email),
            code=payload.code,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    try:
        return await refresh_access_token(
            db,
            refresh_token=payload.refresh_token,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await logout_session(
            db,
            refresh_token=payload.refresh_token,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
