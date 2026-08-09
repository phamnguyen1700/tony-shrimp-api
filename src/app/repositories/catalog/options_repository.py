from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogStatus, Shrimp


async def list_distinct_scalar_values(
    db: AsyncSession,
    column: Any,
    *,
    active_only: bool,
) -> list[str]:
    stmt = (
        select(column)
        .select_from(Shrimp)
        .distinct()
        .where(column.is_not(None))
        .order_by(column)
    )

    if active_only:
        stmt = stmt.where(Shrimp.catalog_status == CatalogStatus.ACTIVE.value)

    result = await db.execute(stmt)
    return [str(value) for value in result.scalars().all() if value]


async def list_distinct_traits(
    db: AsyncSession,
    *,
    active_only: bool,
) -> list[str]:
    where_clause = "WHERE catalog_status = :catalog_status" if active_only else ""
    params = {"catalog_status": CatalogStatus.ACTIVE.value} if active_only else {}

    result = await db.execute(
        text(
            f"""
            SELECT DISTINCT trait
            FROM shrimp, unnest(traits) AS trait
            {where_clause}
            ORDER BY trait
            """
        ),
        params,
    )

    return [str(value) for value in result.scalars().all() if value]


async def list_distinct_array_values(
    db: AsyncSession,
    column: Any,
    *,
    active_only: bool,
) -> list[str]:
    where_clause = "WHERE catalog_status = :catalog_status" if active_only else ""
    params = {"catalog_status": CatalogStatus.ACTIVE.value} if active_only else {}
    column_name = column.key

    result = await db.execute(
        text(
            f"""
            SELECT DISTINCT value
            FROM shrimp, unnest({column_name}) AS value
            {where_clause}
            ORDER BY value
            """
        ),
        params,
    )

    return [str(value) for value in result.scalars().all() if value]
