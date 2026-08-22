import uuid
from decimal import Decimal

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Shrimp, ShrimpVariant


def split_csv_filter(value: str | None) -> list[str]:
    if value is None:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def apply_shrimp_filters(
    statement,
    *,
    catalog_status: str | None = None,
    search: str | None = None,
    species: str | None = None,
    line: str | None = None,
    color: str | None = None,
    grade: str | None = None,
    rarity: str | None = None,
    trait: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    in_stock: bool | None = None,
):
    if catalog_status is not None:
        statement = statement.where(Shrimp.catalog_status == catalog_status)
    if search:
        statement = statement.where(Shrimp.name.ilike(f"%{search}%"))
    if species is not None:
        statement = statement.where(Shrimp.species.ilike(f"{species}%"))
    if line is not None:
        statement = statement.where(Shrimp.line == line)
    if color is not None:
        statement = statement.where(Shrimp.colors.contains([color]))
    if grade is not None:
        statement = statement.where(Shrimp.grade == grade)

    rarity_values = split_csv_filter(rarity)
    if len(rarity_values) > 1:
        statement = statement.where(Shrimp.rarity.in_(rarity_values))
    elif rarity_values:
        statement = statement.where(Shrimp.rarity == rarity_values[0])

    if trait is not None:
        statement = statement.where(Shrimp.traits.contains([trait]))

    variant_filters = [ShrimpVariant.is_active.is_(True)]
    if min_price is not None:
        variant_filters.append(ShrimpVariant.price >= min_price)
    if max_price is not None:
        variant_filters.append(ShrimpVariant.price <= max_price)
    if in_stock is True:
        variant_filters.append(ShrimpVariant.stock_quantity > 0)
    if in_stock is False:
        variant_filters.append(ShrimpVariant.stock_quantity == 0)

    if len(variant_filters) > 1:
        statement = statement.where(Shrimp.variants.any(and_(*variant_filters)))

    return statement


async def create_shrimp(
    db: AsyncSession,
    *,
    name: str,
    slug: str,
    line: str,
    species: str | None = None,
    colors: list[str] | None = None,
    grade: str | None = None,
    rarity: str | None = None,
    description: str | None = None,
    meta_title: str | None = None,
    meta_description: str | None = None,
    catalog_status: str,
    traits: list[str] | None = None,
) -> Shrimp:
    shrimp = Shrimp(
        name=name,
        slug=slug,
        species=species,
        line=line,
        colors=colors or [],
        grade=grade,
        rarity=rarity,
        description=description,
        meta_title=meta_title,
        meta_description=meta_description,
        catalog_status=catalog_status,
        traits=traits or [],
    )
    db.add(shrimp)
    await db.flush()
    return shrimp


async def get_shrimp_by_id(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
) -> Shrimp | None:
    result = await db.execute(
        select(Shrimp)
        .options(
            selectinload(Shrimp.variants),
            selectinload(Shrimp.care_parameter),
            selectinload(Shrimp.images),
        )
        .where(Shrimp.id == shrimp_id)
    )
    return result.scalar_one_or_none()


async def get_shrimp_by_slug(
    db: AsyncSession,
    slug: str,
) -> Shrimp | None:
    result = await db.execute(
        select(Shrimp)
        .options(
            selectinload(Shrimp.variants),
            selectinload(Shrimp.care_parameter),
            selectinload(Shrimp.images),
        )
        .where(Shrimp.slug == slug)
    )
    return result.scalar_one_or_none()


async def list_shrimp(
    db: AsyncSession,
    *,
    catalog_status: str | None = None,
    search: str | None = None,
    species: str | None = None,
    line: str | None = None,
    color: str | None = None,
    grade: str | None = None,
    rarity: str | None = None,
    trait: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    in_stock: bool | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Shrimp]:
    statement = select(Shrimp).options(
        selectinload(Shrimp.variants),
        selectinload(Shrimp.care_parameter),
        selectinload(Shrimp.images),
    )
    statement = apply_shrimp_filters(
        statement,
        catalog_status=catalog_status,
        search=search,
        species=species,
        line=line,
        color=color,
        grade=grade,
        rarity=rarity,
        trait=trait,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
    )

    statement = statement.order_by(Shrimp.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(statement)
    return list(result.scalars().all())


async def list_shrimp_for_filter_options(
    db: AsyncSession,
    *,
    catalog_status: str | None = None,
    search: str | None = None,
    species: str | None = None,
    line: str | None = None,
    color: str | None = None,
    grade: str | None = None,
    rarity: str | None = None,
    trait: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    in_stock: bool | None = None,
) -> list[Shrimp]:
    statement = select(Shrimp).options(
        selectinload(Shrimp.variants),
        selectinload(Shrimp.care_parameter),
        selectinload(Shrimp.images),
    )
    statement = apply_shrimp_filters(
        statement,
        catalog_status=catalog_status,
        search=search,
        species=species,
        line=line,
        color=color,
        grade=grade,
        rarity=rarity,
        trait=trait,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
    )

    result = await db.execute(statement)
    return list(result.scalars().all())


async def update_shrimp(
    db: AsyncSession,
    shrimp: Shrimp,
    *,
    name: str | None = None,
    slug: str | None = None,
    species: str | None = None,
    line: str | None = None,
    colors: list[str] | None = None,
    grade: str | None = None,
    rarity: str | None = None,
    description: str | None = None,
    meta_title: str | None = None,
    meta_description: str | None = None,
    catalog_status: str | None = None,
    traits: list[str] | None = None,
) -> Shrimp:
    if name is not None:
        shrimp.name = name
    if slug is not None:
        shrimp.slug = slug
    if species is not None:
        shrimp.species = species
    if line is not None:
        shrimp.line = line
    if colors is not None:
        shrimp.colors = colors
    if grade is not None:
        shrimp.grade = grade
    if rarity is not None:
        shrimp.rarity = rarity
    if description is not None:
        shrimp.description = description
    if meta_title is not None:
        shrimp.meta_title = meta_title
    if meta_description is not None:
        shrimp.meta_description = meta_description
    if catalog_status is not None:
        shrimp.catalog_status = catalog_status
    if traits is not None:
        shrimp.traits = traits

    await db.flush()
    return shrimp


async def delete_shrimp(
    db: AsyncSession,
    shrimp: Shrimp,
) -> None:
    await db.execute(delete(Shrimp).where(Shrimp.id == shrimp.id))
