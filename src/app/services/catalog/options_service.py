from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CareLevel, CatalogStatus, SaleUnit, Shrimp
from app.repositories.catalog import (
    list_distinct_array_values,
    list_distinct_scalar_values,
    list_distinct_traits,
    list_shrimp_for_filter_options,
)
from app.schemas.catalog import CatalogFilterOptionsResponse, CatalogOptionsResponse
from app.services.catalog.shrimp_service import is_shrimp_available


async def get_catalog_options(
    db: AsyncSession,
    *,
    active_only: bool,
) -> CatalogOptionsResponse:
    return CatalogOptionsResponse(
        catalog_statuses=[status.value for status in CatalogStatus],
        care_levels=[care_level.value for care_level in CareLevel],
        sale_units=[sale_unit.value for sale_unit in SaleUnit],
        lines=await list_distinct_scalar_values(
            db,
            Shrimp.line,
            active_only=active_only,
        ),
        colors=await list_distinct_array_values(
            db,
            Shrimp.colors,
            active_only=active_only,
        ),
        grades=await list_distinct_scalar_values(
            db,
            Shrimp.grade,
            active_only=active_only,
        ),
        rarities=await list_distinct_scalar_values(
            db,
            Shrimp.rarity,
            active_only=active_only,
        ),
        traits=await list_distinct_traits(db, active_only=active_only),
    )


def sorted_unique(values: list[str | None]) -> list[str]:
    return sorted({value for value in values if value})


async def get_catalog_filter_options(
    db: AsyncSession,
    *,
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
) -> CatalogFilterOptionsResponse:
    shrimp_items = await list_shrimp_for_filter_options(
        db,
        catalog_status=CatalogStatus.ACTIVE.value,
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

    availability = []
    if any(is_shrimp_available(shrimp) for shrimp in shrimp_items):
        availability.append("in-stock")
    if any(not is_shrimp_available(shrimp) for shrimp in shrimp_items):
        availability.append("out-of-stock")

    return CatalogFilterOptionsResponse(
        species=sorted_unique([shrimp.species for shrimp in shrimp_items]),
        lines=sorted_unique([shrimp.line for shrimp in shrimp_items]),
        colors=sorted_unique(
            [color for shrimp in shrimp_items for color in shrimp.colors]
        ),
        grades=sorted_unique([shrimp.grade for shrimp in shrimp_items]),
        rarities=sorted_unique([shrimp.rarity for shrimp in shrimp_items]),
        traits=sorted_unique(
            [trait for shrimp in shrimp_items for trait in shrimp.traits]
        ),
        availability=availability,
    )
