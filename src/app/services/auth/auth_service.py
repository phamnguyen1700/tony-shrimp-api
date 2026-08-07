from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_secret,
    normalize_email,
    create_token_lookup_hash,
    verify_secret,
)
from app.repositories.auth import (
    create_session,
    get_or_create_customer_by_email,
    get_session_by_refresh_token_lookup_hash,
    update_session_last_used_at,
    revoke_session,
)
from app.schemas.auth import (
    OtpResponse,
    TokenResponse,
)
from app.services.auth.otp_service import create_otp, verify_otp
from app.services.email import send_otp_email

settings = get_settings()

GENERIC_OTP_MESSAGE = "If the email is valid, a login code has been sent."


async def request_otp(
    redis: Redis,
    email: str,
) -> OtpResponse:
    normalized_email = normalize_email(email)

    code = await create_otp(redis, normalized_email)

    await send_otp_email(
        to_email=normalized_email,
        code=code,
    )
    return OtpResponse(message=GENERIC_OTP_MESSAGE)


async def verify_otp_and_create_session(
    db: AsyncSession,
    redis: Redis,
    *,
    email: str,
    code: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> TokenResponse:
    normalized_email = normalize_email(email)

    is_valid = await verify_otp(redis, normalized_email, code)
    if not is_valid:
        raise ValueError("Invalid or expired OTP code.")

    user = await get_or_create_customer_by_email(db, normalized_email)

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    refresh_token = create_refresh_token()
    refresh_token_hashed = hash_secret(refresh_token)
    refresh_token_lookup_hash = create_token_lookup_hash(refresh_token)
    expires_at = datetime.now(tz=UTC) + timedelta(
        days=settings.refresh_token_expire_days
    )

    await create_session(
        db,
        user_id=user.id,
        refresh_token_hash=refresh_token_hashed,
        refresh_token_lookup_hash=refresh_token_lookup_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def refresh_access_token(
    db: AsyncSession,
    *,
    refresh_token: str,
) -> TokenResponse:
    refresh_token_lookup_hash = create_token_lookup_hash(refresh_token)

    session = await get_session_by_refresh_token_lookup_hash(
        db,
        refresh_token_lookup_hash,
    )
    if session is None:
        raise ValueError("Invalid refresh token.")

    if session.revoked_at is not None:
        raise ValueError("Refresh token has been revoked.")

    if session.expires_at <= datetime.now(UTC):
        raise ValueError("Refresh token has expired.")

    if not verify_secret(refresh_token, session.refresh_token_hash):
        raise ValueError("Invalid refresh token.")

    access_token = create_access_token(
        user_id=session.user.id,
        email=session.user.email,
        role=session.user.role,
    )

    await update_session_last_used_at(db, session)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def logout_session(
    db: AsyncSession,
    *,
    refresh_token: str,
) -> None:
    refresh_token_lookup_hash = create_token_lookup_hash(refresh_token)

    session = await get_session_by_refresh_token_lookup_hash(
        db,
        refresh_token_lookup_hash,
    )
    if session is None:
        raise ValueError("Invalid refresh token.")

    if not verify_secret(refresh_token, session.refresh_token_hash):
        raise ValueError("Invalid refresh token.")

    if session.revoked_at is None:
        await revoke_session(db, session)
        await db.commit()
