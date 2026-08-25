import uuid
import re
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogStatus, Shrimp
from app.repositories.catalog import (
    create_care_parameter,
    create_shrimp,
    create_shrimp_image,
    create_shrimp_variant,
    delete_shrimp,
    get_shrimp_by_id,
    get_shrimp_by_slug,
    list_shrimp,
    update_shrimp,
)
from app.schemas.catalog import (
    CareParameterResponse,
    OwnerShrimpListItemResponse,
    ShrimpCreate,
    ShrimpDetailResponse,
    ShrimpImageResponse,
    ShrimpListItemResponse,
    ShrimpUpdate,
    ShrimpVariantResponse,
)
from app.services.upload import delete_r2_objects


def is_shrimp_available(shrimp: Shrimp) -> bool:
    return any(
        variant.is_active and variant.stock_quantity > 0 for variant in shrimp.variants
    )


def get_active_variants(shrimp: Shrimp):
    return [variant for variant in shrimp.variants if variant.is_active]


def get_min_price(shrimp: Shrimp) -> Decimal | None:
    prices = [variant.price for variant in get_active_variants(shrimp)]
    return min(prices) if prices else None


def get_total_stock(shrimp: Shrimp) -> int:
    return sum(variant.stock_quantity for variant in get_active_variants(shrimp))


def get_primary_image_url(shrimp: Shrimp) -> str | None:
    primary_image = get_primary_image(shrimp)
    return primary_image.url if primary_image is not None else None


def get_sorted_images(shrimp: Shrimp):
    return sorted(shrimp.images, key=lambda image: (image.sort_order, image.created_at))


def get_primary_image(shrimp: Shrimp):
    sorted_images = get_sorted_images(shrimp)
    return sorted_images[0] if sorted_images else None


def to_shrimp_image_response(image, primary_image) -> ShrimpImageResponse:
    return ShrimpImageResponse(
        id=image.id,
        shrimp_id=image.shrimp_id,
        r2_key=image.r2_key,
        url=image.url,
        alt_text=image.alt_text,
        sort_order=image.sort_order,
        is_primary=primary_image is not None and image.id == primary_image.id,
        created_at=image.created_at,
    )


def get_care_level(shrimp: Shrimp) -> str | None:
    if shrimp.care_parameter is None:
        return None

    return shrimp.care_parameter.care_level


def normalize_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "shrimp"


async def create_unique_shrimp_slug(
    db: AsyncSession,
    value: str,
    *,
    current_shrimp_id: uuid.UUID | None = None,
) -> str:
    base_slug = normalize_slug(value)
    candidate = base_slug
    suffix = 2

    while True:
        existing = await get_shrimp_by_slug(db, candidate)
        if existing is None or existing.id == current_shrimp_id:
            return candidate

        candidate = f"{base_slug}-{suffix}"
        suffix += 1


def to_shrimp_list_item_response(shrimp: Shrimp) -> ShrimpListItemResponse:
    primary_image = get_primary_image(shrimp)

    return ShrimpListItemResponse(
        id=shrimp.id,
        name=shrimp.name,
        slug=shrimp.slug,
        species=shrimp.species,
        line=shrimp.line,
        colors=shrimp.colors,
        grade=shrimp.grade,
        rarity=shrimp.rarity,
        description=shrimp.description,
        meta_title=shrimp.meta_title,
        meta_description=shrimp.meta_description,
        catalog_status=shrimp.catalog_status,
        traits=shrimp.traits,
        created_at=shrimp.created_at,
        updated_at=shrimp.updated_at,
        is_available=is_shrimp_available(shrimp),
        min_price=get_min_price(shrimp),
        total_stock=get_total_stock(shrimp),
        primary_image_url=primary_image.url if primary_image is not None else None,
        care_level=get_care_level(shrimp),
    )


def to_owner_shrimp_list_item_response(shrimp: Shrimp) -> OwnerShrimpListItemResponse:
    primary_image = get_primary_image(shrimp)

    return OwnerShrimpListItemResponse(
        **to_shrimp_list_item_response(shrimp).model_dump(),
        images=[
            to_shrimp_image_response(image, primary_image)
            for image in get_sorted_images(shrimp)
        ],
    )


def to_shrimp_detail_response(shrimp: Shrimp) -> ShrimpDetailResponse:
    primary_image = get_primary_image(shrimp)

    return ShrimpDetailResponse(
        id=shrimp.id,
        name=shrimp.name,
        slug=shrimp.slug,
        species=shrimp.species,
        line=shrimp.line,
        colors=shrimp.colors,
        grade=shrimp.grade,
        rarity=shrimp.rarity,
        description=shrimp.description,
        meta_title=shrimp.meta_title,
        meta_description=shrimp.meta_description,
        catalog_status=shrimp.catalog_status,
        traits=shrimp.traits,
        created_at=shrimp.created_at,
        updated_at=shrimp.updated_at,
        is_available=is_shrimp_available(shrimp),
        variants=[
            ShrimpVariantResponse(
                id=variant.id,
                shrimp_id=variant.shrimp_id,
                name=variant.name,
                sale_unit=variant.sale_unit,
                sale_quantity=variant.sale_quantity,
                price=variant.price,
                stock_quantity=variant.stock_quantity,
                is_active=variant.is_active,
                created_at=variant.created_at,
                updated_at=variant.updated_at,
            )
            for variant in shrimp.variants
        ],
        care_parameter=(
            CareParameterResponse(
                id=shrimp.care_parameter.id,
                shrimp_id=shrimp.care_parameter.shrimp_id,
                ph_min=shrimp.care_parameter.ph_min,
                ph_max=shrimp.care_parameter.ph_max,
                gh_min=shrimp.care_parameter.gh_min,
                gh_max=shrimp.care_parameter.gh_max,
                kh_min=shrimp.care_parameter.kh_min,
                kh_max=shrimp.care_parameter.kh_max,
                tds_min=shrimp.care_parameter.tds_min,
                tds_max=shrimp.care_parameter.tds_max,
                temperature_min=shrimp.care_parameter.temperature_min,
                temperature_max=shrimp.care_parameter.temperature_max,
                care_level=shrimp.care_parameter.care_level,
            )
            if shrimp.care_parameter is not None
            else None
        ),
        images=[
            to_shrimp_image_response(image, primary_image)
            for image in get_sorted_images(shrimp)
        ],
    )


async def create_shrimp_catalog_item(
    db: AsyncSession,
    payload: ShrimpCreate,
) -> ShrimpDetailResponse:
    shrimp = await create_shrimp(
        db,
        name=payload.name,
        slug=await create_unique_shrimp_slug(db, payload.slug or payload.name),
        species=payload.species,
        line=payload.line,
        colors=payload.colors,
        grade=payload.grade,
        rarity=payload.rarity,
        description=payload.description,
        meta_title=payload.meta_title,
        meta_description=payload.meta_description,
        catalog_status=payload.catalog_status.value,
        traits=payload.traits,
    )

    for variant in payload.variants:
        await create_shrimp_variant(
            db,
            shrimp_id=shrimp.id,
            name=variant.name,
            sale_unit=variant.sale_unit.value,
            sale_quantity=variant.sale_quantity,
            price=variant.price,
            stock_quantity=variant.stock_quantity,
            is_active=variant.is_active,
        )

    if payload.care_parameter is not None:
        await create_care_parameter(
            db,
            shrimp_id=shrimp.id,
            ph_min=payload.care_parameter.ph_min,
            ph_max=payload.care_parameter.ph_max,
            gh_min=payload.care_parameter.gh_min,
            gh_max=payload.care_parameter.gh_max,
            kh_min=payload.care_parameter.kh_min,
            kh_max=payload.care_parameter.kh_max,
            tds_min=payload.care_parameter.tds_min,
            tds_max=payload.care_parameter.tds_max,
            temperature_min=payload.care_parameter.temperature_min,
            temperature_max=payload.care_parameter.temperature_max,
            care_level=payload.care_parameter.care_level.value,
        )

    for image in payload.images:
        await create_shrimp_image(
            db,
            shrimp_id=shrimp.id,
            r2_key=image.r2_key,
            url=str(image.url) if image.url else None,
            alt_text=image.alt_text,
            sort_order=image.sort_order,
            is_primary=image.is_primary,
        )

    await db.commit()

    created = await get_shrimp_by_id(db, shrimp.id)
    if created is None:
        raise ValueError("Created shrimp could not be loaded.")

    return to_shrimp_detail_response(created)


async def get_shrimp_catalog_item(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
    *,
    active_only: bool = False,
) -> ShrimpDetailResponse:
    shrimp = await get_shrimp_by_id(db, shrimp_id)
    if shrimp is None or (
        active_only and shrimp.catalog_status != CatalogStatus.ACTIVE.value
    ):
        raise ValueError("Shrimp not found.")

    return to_shrimp_detail_response(shrimp)


async def get_shrimp_catalog_item_by_slug(
    db: AsyncSession,
    slug: str,
    *,
    active_only: bool = False,
) -> ShrimpDetailResponse:
    shrimp = await get_shrimp_by_slug(db, slug)
    if shrimp is None or (
        active_only and shrimp.catalog_status != CatalogStatus.ACTIVE.value
    ):
        raise ValueError("Shrimp not found.")

    return to_shrimp_detail_response(shrimp)


async def list_shrimp_catalog_items(
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
) -> list[ShrimpListItemResponse]:
    shrimp_items = await list_shrimp(
        db,
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
        limit=limit,
        offset=offset,
    )

    return [to_shrimp_list_item_response(shrimp) for shrimp in shrimp_items]


async def list_owner_shrimp_catalog_items(
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
) -> list[OwnerShrimpListItemResponse]:
    shrimp_items = await list_shrimp(
        db,
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
        limit=limit,
        offset=offset,
    )

    return [to_owner_shrimp_list_item_response(shrimp) for shrimp in shrimp_items]


async def update_shrimp_catalog_item(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
    payload: ShrimpUpdate,
) -> ShrimpDetailResponse:
    shrimp = await get_shrimp_by_id(db, shrimp_id)
    if shrimp is None:
        raise ValueError("Shrimp not found.")

    shrimp = await update_shrimp(
        db,
        shrimp,
        name=payload.name,
        slug=(
            await create_unique_shrimp_slug(
                db,
                payload.slug,
                current_shrimp_id=shrimp.id,
            )
            if payload.slug is not None
            else None
        ),
        species=payload.species,
        line=payload.line,
        colors=payload.colors,
        grade=payload.grade,
        rarity=payload.rarity,
        description=payload.description,
        meta_title=payload.meta_title,
        meta_description=payload.meta_description,
        catalog_status=payload.catalog_status.value if payload.catalog_status else None,
        traits=payload.traits,
    )
    if "meta_title" in payload.model_fields_set:
        shrimp.meta_title = payload.meta_title
    if "meta_description" in payload.model_fields_set:
        shrimp.meta_description = payload.meta_description

    await db.commit()

    updated = await get_shrimp_by_id(db, shrimp.id)
    if updated is None:
        raise ValueError("Updated shrimp could not be loaded.")

    return to_shrimp_detail_response(updated)


async def set_shrimp_catalog_status(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
    catalog_status: CatalogStatus,
) -> ShrimpDetailResponse:
    shrimp = await get_shrimp_by_id(db, shrimp_id)
    if shrimp is None:
        raise ValueError("Shrimp not found.")

    shrimp = await update_shrimp(
        db,
        shrimp,
        catalog_status=catalog_status.value,
    )
    await db.commit()

    updated = await get_shrimp_by_id(db, shrimp.id)
    if updated is None:
        raise ValueError("Updated shrimp could not be loaded.")

    return to_shrimp_detail_response(updated)


async def delete_inactive_shrimp_catalog_item(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
) -> None:
    shrimp = await get_shrimp_by_id(db, shrimp_id)
    if shrimp is None:
        raise ValueError("Shrimp not found.")
    if shrimp.catalog_status != CatalogStatus.INACTIVE.value:
        raise ValueError("Only inactive shrimp can be deleted.")

    delete_r2_objects([image.r2_key for image in shrimp.images])
    await delete_shrimp(db, shrimp)
    await db.commit()
