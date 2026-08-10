import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserAddress


async def list_user_addresses(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[UserAddress]:
    result = await db.execute(
        select(UserAddress)
        .where(UserAddress.user_id == user_id)
        .order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc())
    )
    return list(result.scalars().all())


async def get_user_address(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    address_id: uuid.UUID,
) -> UserAddress | None:
    result = await db.execute(
        select(UserAddress).where(
            UserAddress.id == address_id,
            UserAddress.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def count_user_addresses(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    addresses = await list_user_addresses(db, user_id)
    return len(addresses)


async def unset_default_user_addresses(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> None:
    await db.execute(
        update(UserAddress)
        .where(UserAddress.user_id == user_id)
        .values(is_default=False)
    )


async def create_user_address(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    recipient_name: str,
    recipient_phone_encrypted: str,
    address_line1_encrypted: str,
    address_line2_encrypted: str | None,
    suburb: str,
    state: str,
    postcode: str,
    is_default: bool,
) -> UserAddress:
    address = UserAddress(
        user_id=user_id,
        recipient_name=recipient_name,
        recipient_phone_encrypted=recipient_phone_encrypted,
        address_line1_encrypted=address_line1_encrypted,
        address_line2_encrypted=address_line2_encrypted,
        suburb=suburb,
        state=state,
        postcode=postcode,
        is_default=is_default,
    )
    db.add(address)
    await db.flush()
    return address


async def delete_user_address(
    db: AsyncSession,
    address: UserAddress,
) -> None:
    await db.delete(address)
    await db.flush()


async def set_user_address_as_default(
    db: AsyncSession,
    address: UserAddress,
) -> UserAddress:
    await unset_default_user_addresses(db, address.user_id)
    address.is_default = True
    await db.flush()
    return address
