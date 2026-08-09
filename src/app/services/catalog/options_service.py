from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CareLevel, CatalogStatus, SaleUnit, Shrimp
from app.repositories.catalog import (
    list_distinct_array_values,
    list_distinct_scalar_values,
    list_distinct_traits,
)
from app.schemas.catalog import CatalogOptionsResponse


async def get_catalog_options(
    db: AsyncSession,
    *,
    active_only: bool,
) -> CatalogOptionsResponse:
    return CatalogOptionsResponse(
        catalog_statuses=[status.value for status in CatalogStatus],
        care_levels=[care_level.value for care_level in CareLevel],
        sale_units=[sale_unit.value for sale_unit in SaleUnit],
        types=await list_distinct_scalar_values(
            db,
            Shrimp.type,
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
