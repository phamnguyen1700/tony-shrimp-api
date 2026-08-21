import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pii import decrypt_pii
from app.models.auth import User, UserRole, UserStatus
from app.repositories.auth import (
    activate_user,
    count_users,
    deactivate_user,
    delete_user,
    get_user_detail_by_id,
    list_users,
    update_user_role,
)
from app.schemas.user import (
    OwnerUserDetailResponse,
    OwnerUserListItemResponse,
    OwnerUserListResponse,
)
from app.services.user.address_service import build_address_response


def assert_can_manage_user(actor: User, target: User) -> None:
    if actor.id == target.id:
        raise ValueError("You cannot manage your own user account here.")

    if actor.role == UserRole.OWNER.value and target.role != UserRole.CUSTOMER.value:
        raise PermissionError("Owner can only manage customer accounts.")


def build_owner_user_list_item(user: User) -> OwnerUserListItemResponse:
    profile = user.profile

    return OwnerUserListItemResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        status=user.status,
        full_name=profile.full_name if profile else None,
        phone=decrypt_pii(profile.phone_encrypted) if profile else None,
        created_at=user.created_at,
        updated_at=user.updated_at,
        deactivated_at=user.deactivated_at,
    )


def build_owner_user_detail(user: User) -> OwnerUserDetailResponse:
    return OwnerUserDetailResponse(
        **build_owner_user_list_item(user).model_dump(),
        addresses=[build_address_response(address) for address in user.addresses],
    )


async def list_owner_users(
    db: AsyncSession,
    *,
    actor: User,
    search: str | None = None,
    role: UserRole | None = None,
    role_in: str | None = None,
    status: UserStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> OwnerUserListResponse:
    role_value = role.value if role else None
    role_values = [
        value.strip()
        for value in (role_in or "").split(",")
        if value.strip() in {role.value for role in UserRole}
    ]
    if role_value:
        role_values = []

    status_value = status.value if status else None

    users = await list_users(
        db,
        search=search,
        role=role_value,
        role_in=role_values or None,
        status=status_value,
        limit=limit,
        offset=offset,
    )
    total = await count_users(
        db,
        search=search,
        role=role_value,
        role_in=role_values or None,
        status=status_value,
    )

    return OwnerUserListResponse(
        items=[build_owner_user_list_item(user) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_owner_user_detail(
    db: AsyncSession,
    *,
    actor: User,
    user_id: uuid.UUID,
) -> OwnerUserDetailResponse:
    user = await get_user_detail_by_id(db, user_id)
    if user is None:
        raise ValueError("User not found.")

    return build_owner_user_detail(user)


async def activate_owner_user(
    db: AsyncSession,
    *,
    actor: User,
    user_id: uuid.UUID,
) -> OwnerUserDetailResponse:
    user = await get_user_detail_by_id(db, user_id)
    if user is None:
        raise ValueError("User not found.")

    assert_can_manage_user(actor, user)
    user = await activate_user(db, user)
    await db.commit()
    await db.refresh(user, attribute_names=["profile", "addresses"])

    return build_owner_user_detail(user)


async def deactivate_owner_user(
    db: AsyncSession,
    *,
    actor: User,
    user_id: uuid.UUID,
) -> OwnerUserDetailResponse:
    user = await get_user_detail_by_id(db, user_id)
    if user is None:
        raise ValueError("User not found.")

    assert_can_manage_user(actor, user)
    user = await deactivate_user(db, user)
    await db.commit()
    await db.refresh(user, attribute_names=["profile", "addresses"])

    return build_owner_user_detail(user)


async def update_owner_user_role(
    db: AsyncSession,
    *,
    actor: User,
    user_id: uuid.UUID,
    role: UserRole,
) -> OwnerUserDetailResponse:
    user = await get_user_detail_by_id(db, user_id)
    if user is None:
        raise ValueError("User not found.")

    if actor.id == user.id:
        raise ValueError("You cannot change your own role.")

    user = await update_user_role(db, user, role)
    await db.commit()
    await db.refresh(user, attribute_names=["profile", "addresses"])

    return build_owner_user_detail(user)


async def delete_inactive_owner_user(
    db: AsyncSession,
    *,
    actor: User,
    user_id: uuid.UUID,
) -> None:
    user = await get_user_detail_by_id(db, user_id)
    if user is None:
        raise ValueError("User not found.")

    assert_can_manage_user(actor, user)
    if user.status != UserStatus.INACTIVE.value:
        raise ValueError("Only inactive users can be deleted.")

    await delete_user(db, user)
    await db.commit()
