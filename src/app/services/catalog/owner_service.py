import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.catalog import (
    create_care_parameter,
    create_shrimp_image,
    create_shrimp_variant,
    delete_shrimp_image,
    delete_shrimp_variant,
    get_care_parameter_by_shrimp_id,
    get_shrimp_by_id,
    get_shrimp_image_by_id,
    get_shrimp_variant_by_id,
    update_care_parameter,
    update_shrimp_image,
    update_shrimp_variant,
)
from app.schemas.catalog import (
    CareParameterCreate,
    CareParameterUpdate,
    ShrimpDetailResponse,
    ShrimpImageCreate,
    ShrimpImageUpdate,
    ShrimpVariantCreate,
    ShrimpVariantUpdate,
)
from app.services.catalog.shrimp_service import to_shrimp_detail_response
from app.services.upload import delete_r2_object

MAX_SHRIMP_IMAGES = 4


async def load_shrimp_detail_response(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
) -> ShrimpDetailResponse:
    shrimp = await get_shrimp_by_id(db, shrimp_id)
    if shrimp is None:
        raise ValueError("Shrimp not found.")

    return to_shrimp_detail_response(shrimp)


async def add_shrimp_variant(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
    payload: ShrimpVariantCreate,
) -> ShrimpDetailResponse:
    if await get_shrimp_by_id(db, shrimp_id) is None:
        raise ValueError("Shrimp not found.")

    await create_shrimp_variant(
        db,
        shrimp_id=shrimp_id,
        name=payload.name,
        sale_unit=payload.sale_unit.value,
        sale_quantity=payload.sale_quantity,
        price=payload.price,
        stock_quantity=payload.stock_quantity,
        is_active=payload.is_active,
    )
    await db.commit()

    return await load_shrimp_detail_response(db, shrimp_id)


async def edit_shrimp_variant(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
    variant_id: uuid.UUID,
    payload: ShrimpVariantUpdate,
) -> ShrimpDetailResponse:
    variant = await get_shrimp_variant_by_id(
        db,
        shrimp_id=shrimp_id,
        variant_id=variant_id,
    )
    if variant is None:
        raise ValueError("Shrimp variant not found.")

    await update_shrimp_variant(
        db,
        variant,
        name=payload.name,
        sale_unit=payload.sale_unit.value if payload.sale_unit else None,
        sale_quantity=payload.sale_quantity,
        price=payload.price,
        stock_quantity=payload.stock_quantity,
        is_active=payload.is_active,
    )
    await db.commit()

    return await load_shrimp_detail_response(db, shrimp_id)


async def remove_shrimp_variant(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
    variant_id: uuid.UUID,
) -> ShrimpDetailResponse:
    variant = await get_shrimp_variant_by_id(
        db,
        shrimp_id=shrimp_id,
        variant_id=variant_id,
    )
    if variant is None:
        raise ValueError("Shrimp variant not found.")

    await delete_shrimp_variant(db, shrimp_id=shrimp_id, variant_id=variant_id)
    await db.commit()

    return await load_shrimp_detail_response(db, shrimp_id)


async def upsert_shrimp_care_parameter(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
    payload: CareParameterCreate | CareParameterUpdate,
) -> ShrimpDetailResponse:
    if await get_shrimp_by_id(db, shrimp_id) is None:
        raise ValueError("Shrimp not found.")

    care_parameter = await get_care_parameter_by_shrimp_id(db, shrimp_id)
    if care_parameter is None:
        await create_care_parameter(
            db,
            shrimp_id=shrimp_id,
            ph_min=payload.ph_min,
            ph_max=payload.ph_max,
            gh_min=payload.gh_min,
            gh_max=payload.gh_max,
            kh_min=payload.kh_min,
            kh_max=payload.kh_max,
            tds_min=payload.tds_min,
            tds_max=payload.tds_max,
            temperature_min=payload.temperature_min,
            temperature_max=payload.temperature_max,
            care_level=payload.care_level.value if payload.care_level else "beginner",
        )
    else:
        await update_care_parameter(
            db,
            care_parameter,
            ph_min=payload.ph_min,
            ph_max=payload.ph_max,
            gh_min=payload.gh_min,
            gh_max=payload.gh_max,
            kh_min=payload.kh_min,
            kh_max=payload.kh_max,
            tds_min=payload.tds_min,
            tds_max=payload.tds_max,
            temperature_min=payload.temperature_min,
            temperature_max=payload.temperature_max,
            care_level=payload.care_level.value if payload.care_level else None,
        )

    await db.commit()
    return await load_shrimp_detail_response(db, shrimp_id)

async def add_shrimp_image(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
    payload: ShrimpImageCreate,
) -> ShrimpDetailResponse:
    shrimp = await get_shrimp_by_id(db, shrimp_id)
    if shrimp is None:
        raise ValueError("Shrimp not found.")
    if len(shrimp.images) >= MAX_SHRIMP_IMAGES:
        raise ValueError("Each shrimp can have at most 4 images.")

    is_primary = len(shrimp.images) == 0

    await create_shrimp_image(
        db,
        shrimp_id=shrimp_id,
        r2_key=payload.r2_key,
        url=str(payload.url) if payload.url else None,
        alt_text=payload.alt_text,
        sort_order=len(shrimp.images),
        is_primary=is_primary,
    )
    await db.commit()

    return await load_shrimp_detail_response(db, shrimp_id)


async def edit_shrimp_image(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
    image_id: uuid.UUID,
    payload: ShrimpImageUpdate,
) -> ShrimpDetailResponse:
    image = await get_shrimp_image_by_id(db, shrimp_id=shrimp_id, image_id=image_id)
    if image is None:
        raise ValueError("Shrimp image not found.")

    await update_shrimp_image(
        db,
        image,
        alt_text=payload.alt_text,
        sort_order=payload.sort_order,
    )
    await db.commit()

    return await load_shrimp_detail_response(db, shrimp_id)


async def remove_shrimp_image(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
    image_id: uuid.UUID,
) -> ShrimpDetailResponse:
    image = await get_shrimp_image_by_id(db, shrimp_id=shrimp_id, image_id=image_id)
    if image is None:
        raise ValueError("Shrimp image not found.")

    delete_r2_object(image.r2_key)
    await delete_shrimp_image(db, shrimp_id=shrimp_id, image_id=image_id)
    await db.commit()

    return await load_shrimp_detail_response(db, shrimp_id)
