import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth.session import Session


async def create_session(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    refresh_token_hash: str,
    refresh_token_lookup_hash: str,
    expires_at: datetime,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Session:
    session = Session(
        user_id=user_id,
        refresh_token_hash=refresh_token_hash,
        refresh_token_lookup_hash=refresh_token_lookup_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(session)
    await db.flush()
    return session


async def get_session_by_refresh_token_lookup_hash(
    db: AsyncSession,
    refresh_token_lookup_hash: str,
) -> Session | None:
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.user))
        .where(Session.refresh_token_lookup_hash == refresh_token_lookup_hash)
    )
    return result.scalar_one_or_none()


async def revoke_session(
    db: AsyncSession,
    session: Session,
) -> Session:
    session.revoked_at = datetime.now(UTC)
    await db.flush()
    return session


async def update_session_last_used_at(
    db: AsyncSession,
    session: Session,
) -> Session:
    session.last_used_at = datetime.now(UTC)
    await db.flush()
    return session
