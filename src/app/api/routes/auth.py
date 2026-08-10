from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_redis_client, get_current_user
from app.core.config import get_settings
from app.schemas.auth import AuthResponse, OtpRequest, OtpResponse, VerifyOtpRequest
from app.schemas.auth.auth import LogoutRequest, RefreshTokenRequest
from app.services.auth import request_otp, verify_otp_and_create_session

from app.models.auth.user import User
from app.schemas.auth import CurrentUserResponse
from app.services.auth.auth_service import (
    logout_session,
    refresh_access_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
) -> None:
    cookie_options = {
        "httponly": True,
        "secure": settings.auth_cookie_secure,
        "samesite": settings.auth_cookie_samesite,
        "domain": settings.auth_cookie_domain or None,
        "path": "/",
    }
    response.set_cookie(
        key=settings.access_token_cookie_name,
        value=access_token,
        max_age=settings.access_token_expire_minutes * 60,
        **cookie_options,
    )
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        **cookie_options,
    )


def clear_auth_cookies(response: Response) -> None:
    cookie_options = {
        "httponly": True,
        "secure": settings.auth_cookie_secure,
        "samesite": settings.auth_cookie_samesite,
        "domain": settings.auth_cookie_domain or None,
        "path": "/",
    }
    response.delete_cookie(settings.access_token_cookie_name, **cookie_options)
    response.delete_cookie(settings.refresh_token_cookie_name, **cookie_options)


def get_refresh_token_from_request(
    request: Request,
    payload: RefreshTokenRequest | LogoutRequest | None,
) -> str | None:
    if payload and payload.refresh_token:
        return payload.refresh_token

    return request.cookies.get(settings.refresh_token_cookie_name)


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


@router.post("/verify-otp", response_model=AuthResponse)
async def verify_login_otp(
    payload: VerifyOtpRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
) -> AuthResponse:
    try:
        auth_response, access_token, refresh_token = await verify_otp_and_create_session(
            db,
            redis,
            email=str(payload.email),
            code=payload.code,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        set_auth_cookies(
            response,
            access_token=access_token,
            refresh_token=refresh_token,
        )
        return auth_response
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


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    request: Request,
    response: Response,
    payload: RefreshTokenRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    refresh_token_value = get_refresh_token_from_request(request, payload)
    if refresh_token_value is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token.",
        )

    try:
        auth_response, access_token, refresh_token_value = await refresh_access_token(
            db,
            refresh_token=refresh_token_value,
        )
        set_auth_cookies(
            response,
            access_token=access_token,
            refresh_token=refresh_token_value,
        )
        return auth_response
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    payload: LogoutRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    refresh_token_value = get_refresh_token_from_request(request, payload)
    if refresh_token_value is None:
        clear_auth_cookies(response)
        return

    try:
        await logout_session(
            db,
            refresh_token=refresh_token_value,
        )
        clear_auth_cookies(response)
    except ValueError as exc:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
