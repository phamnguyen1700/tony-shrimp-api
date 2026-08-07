import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.user import User, UserRole


async def get_user_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    role: UserRole = UserRole.CUSTOMER,
) -> User:
    user = User(email=email, role=role.value)
    db.add(user)
    await db.flush()
    return user


async def get_or_create_customer_by_email(
    db: AsyncSession,
    email: str,
) -> User:
    user = await get_user_by_email(db, email)
    if user is not None:
        return user

    return await create_user(
        db=db,
        email=email,
        role=UserRole.CUSTOMER,
    )
