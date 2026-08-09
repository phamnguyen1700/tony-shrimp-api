import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CareParameter


async def create_care_parameter(
    db: AsyncSession,
    *,
    shrimp_id: uuid.UUID,
    ph_min: float | None = None,
    ph_max: float | None = None,
    gh_min: float | None = None,
    gh_max: float | None = None,
    kh_min: float | None = None,
    kh_max: float | None = None,
    tds_min: int | None = None,
    tds_max: int | None = None,
    temperature_min: float | None = None,
    temperature_max: float | None = None,
    care_level: str = "beginner",
) -> CareParameter:
    care_parameter = CareParameter(
        shrimp_id=shrimp_id,
        ph_min=ph_min,
        ph_max=ph_max,
        gh_min=gh_min,
        gh_max=gh_max,
        kh_min=kh_min,
        kh_max=kh_max,
        tds_min=tds_min,
        tds_max=tds_max,
        temperature_min=temperature_min,
        temperature_max=temperature_max,
        care_level=care_level,
    )
    db.add(care_parameter)
    await db.flush()
    return care_parameter


async def get_care_parameter_by_shrimp_id(
    db: AsyncSession,
    shrimp_id: uuid.UUID,
) -> CareParameter | None:
    result = await db.execute(
        select(CareParameter).where(CareParameter.shrimp_id == shrimp_id)
    )
    return result.scalar_one_or_none()


async def update_care_parameter(
    db: AsyncSession,
    care_parameter: CareParameter,
    *,
    ph_min: float | None = None,
    ph_max: float | None = None,
    gh_min: float | None = None,
    gh_max: float | None = None,
    kh_min: float | None = None,
    kh_max: float | None = None,
    tds_min: int | None = None,
    tds_max: int | None = None,
    temperature_min: float | None = None,
    temperature_max: float | None = None,
    care_level: str | None = None,
) -> CareParameter:
    if ph_min is not None:
        care_parameter.ph_min = ph_min
    if ph_max is not None:
        care_parameter.ph_max = ph_max
    if gh_min is not None:
        care_parameter.gh_min = gh_min
    if gh_max is not None:
        care_parameter.gh_max = gh_max
    if kh_min is not None:
        care_parameter.kh_min = kh_min
    if kh_max is not None:
        care_parameter.kh_max = kh_max
    if tds_min is not None:
        care_parameter.tds_min = tds_min
    if tds_max is not None:
        care_parameter.tds_max = tds_max
    if temperature_min is not None:
        care_parameter.temperature_min = temperature_min
    if temperature_max is not None:
        care_parameter.temperature_max = temperature_max
    if care_level is not None:
        care_parameter.care_level = care_level

    await db.flush()
    return care_parameter
