import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserProfile


async def get_user_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UserProfile | None:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    return result.scalar_one_or_none()


async def create_user_profile(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    full_name: str | None = None,
    phone_encrypted: str | None = None,
) -> UserProfile:
    profile = UserProfile(
        user_id=user_id,
        full_name=full_name,
        phone_encrypted=phone_encrypted,
    )
    db.add(profile)
    await db.flush()
    return profile


async def get_or_create_user_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UserProfile:
    profile = await get_user_profile(db, user_id)
    if profile is not None:
        return profile

    return await create_user_profile(db, user_id=user_id)


async def update_user_profile(
    db: AsyncSession,
    profile: UserProfile,
    *,
    full_name: str | None = None,
    phone_encrypted: str | None = None,
) -> UserProfile:
    profile.full_name = full_name
    profile.phone_encrypted = phone_encrypted
    await db.flush()
    return profile
