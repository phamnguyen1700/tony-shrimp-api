import uuid
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import ShrimpVariant


async def create_shrimp_variant(
    db: AsyncSession,
    *,
    shrimp_id: uuid.UUID,
    name: str,
    sale_unit: str,
    sale_quantity: int,
    price: Decimal,
    stock_quantity: int = 0,
    is_active: bool = True,
) -> ShrimpVariant:
    variant = ShrimpVariant(
        shrimp_id=shrimp_id,
        name=name,
        sale_unit=sale_unit,
        sale_quantity=sale_quantity,
        price=price,
        stock_quantity=stock_quantity,
        is_active=is_active,
    )
    db.add(variant)
    await db.flush()
    return variant


async def get_shrimp_variant_by_id(
    db: AsyncSession,
    *,
    shrimp_id: uuid.UUID,
    variant_id: uuid.UUID,
) -> ShrimpVariant | None:
    result = await db.execute(
        select(ShrimpVariant).where(
            ShrimpVariant.id == variant_id,
            ShrimpVariant.shrimp_id == shrimp_id,
        )
    )
    return result.scalar_one_or_none()


async def update_shrimp_variant(
    db: AsyncSession,
    variant: ShrimpVariant,
    *,
    name: str | None = None,
    sale_unit: str | None = None,
    sale_quantity: int | None = None,
    price: Decimal | None = None,
    stock_quantity: int | None = None,
    is_active: bool | None = None,
) -> ShrimpVariant:
    if name is not None:
        variant.name = name
    if sale_unit is not None:
        variant.sale_unit = sale_unit
    if sale_quantity is not None:
        variant.sale_quantity = sale_quantity
    if price is not None:
        variant.price = price
    if stock_quantity is not None:
        variant.stock_quantity = stock_quantity
    if is_active is not None:
        variant.is_active = is_active

    await db.flush()
    return variant


async def delete_shrimp_variant(
    db: AsyncSession,
    *,
    shrimp_id: uuid.UUID,
    variant_id: uuid.UUID,
) -> None:
    await db.execute(
        delete(ShrimpVariant).where(
            ShrimpVariant.id == variant_id,
            ShrimpVariant.shrimp_id == shrimp_id,
        )
    )
