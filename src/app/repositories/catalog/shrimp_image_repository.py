import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import ShrimpImage


async def create_shrimp_image(
    db: AsyncSession,
    *,
    shrimp_id: uuid.UUID,
    r2_key: str,
    url: str | None = None,
    alt_text: str | None = None,
    sort_order: int = 0,
    is_primary: bool = False,
) -> ShrimpImage:
    image = ShrimpImage(
        shrimp_id=shrimp_id,
        r2_key=r2_key,
        url=url,
        alt_text=alt_text,
        sort_order=sort_order,
        is_primary=is_primary,
    )
    db.add(image)
    await db.flush()
    return image


async def get_shrimp_image_by_id(
    db: AsyncSession,
    *,
    shrimp_id: uuid.UUID,
    image_id: uuid.UUID,
) -> ShrimpImage | None:
    result = await db.execute(
        select(ShrimpImage).where(
            ShrimpImage.id == image_id,
            ShrimpImage.shrimp_id == shrimp_id,
        )
    )
    return result.scalar_one_or_none()


async def update_shrimp_image(
    db: AsyncSession,
    image: ShrimpImage,
    *,
    alt_text: str | None = None,
    sort_order: int | None = None,
) -> ShrimpImage:
    if alt_text is not None:
        image.alt_text = alt_text
    if sort_order is not None:
        image.sort_order = sort_order

    await db.flush()
    return image


async def delete_shrimp_image(
    db: AsyncSession,
    *,
    shrimp_id: uuid.UUID,
    image_id: uuid.UUID,
) -> None:
    await db.execute(
        delete(ShrimpImage).where(
            ShrimpImage.id == image_id,
            ShrimpImage.shrimp_id == shrimp_id,
        )
    )
