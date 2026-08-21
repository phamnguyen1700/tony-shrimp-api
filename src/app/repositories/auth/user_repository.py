import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth.user import User, UserRole, UserStatus
from app.models.user import UserProfile


async def get_user_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_detail_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.profile), selectinload(User.addresses))
        .where(User.id == user_id)
    )
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


def build_user_list_filters(
    *,
    search: str | None = None,
    role: str | None = None,
    role_in: list[str] | None = None,
    status: str | None = None,
) -> list[object]:
    filters: list[object] = []

    if search:
        search_pattern = f"%{search.strip().lower()}%"
        filters.append(
            or_(
                func.lower(User.email).like(search_pattern),
                func.lower(UserProfile.full_name).like(search_pattern),
            )
        )

    if role:
        filters.append(User.role == role)

    if role_in:
        filters.append(User.role.in_(role_in))

    if status:
        filters.append(User.status == status)

    return filters


async def list_users(
    db: AsyncSession,
    *,
    search: str | None = None,
    role: str | None = None,
    role_in: list[str] | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[User]:
    filters = build_user_list_filters(
        search=search,
        role=role,
        role_in=role_in,
        status=status,
    )
    query = select(User).options(selectinload(User.profile))
    if search:
        query = query.outerjoin(UserProfile)

    result = await db.execute(
        query
        .where(*filters)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def count_users(
    db: AsyncSession,
    *,
    search: str | None = None,
    role: str | None = None,
    role_in: list[str] | None = None,
    status: str | None = None,
) -> int:
    filters = build_user_list_filters(
        search=search,
        role=role,
        role_in=role_in,
        status=status,
    )
    query = select(func.count()).select_from(User)
    if search:
        query = query.outerjoin(UserProfile)

    result = await db.execute(query.where(*filters))
    return int(result.scalar_one())


async def activate_user(
    db: AsyncSession,
    user: User,
) -> User:
    user.status = UserStatus.ACTIVE.value
    user.deactivated_at = None
    await db.flush()
    return user


async def deactivate_user(
    db: AsyncSession,
    user: User,
) -> User:
    user.status = UserStatus.INACTIVE.value
    user.deactivated_at = datetime.now(UTC)
    await db.flush()
    return user


async def update_user_role(
    db: AsyncSession,
    user: User,
    role: UserRole,
) -> User:
    user.role = role.value
    await db.flush()
    return user


async def delete_user(
    db: AsyncSession,
    user: User,
) -> None:
    await db.delete(user)
    await db.flush()


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
