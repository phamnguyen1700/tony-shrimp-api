import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.models.catalog import CatalogStatus
from app.schemas.catalog import (
    CatalogOptionsResponse,
    ShrimpDetailResponse,
    ShrimpListItemResponse,
)
from app.services.catalog import (
    get_catalog_options,
    get_shrimp_catalog_item,
    get_shrimp_catalog_item_by_slug,
    list_shrimp_catalog_items,
)

router = APIRouter(prefix="/catalog", tags=["catalog - public"])


@router.get("/options", response_model=CatalogOptionsResponse)
async def get_public_catalog_options(
    db: AsyncSession = Depends(get_db_session),
) -> CatalogOptionsResponse:
    return await get_catalog_options(db, active_only=True)


@router.get("/shrimp", response_model=list[ShrimpListItemResponse])
async def list_shrimp(
    search: str | None = Query(default=None),
    line: str | None = Query(default=None),
    color: str | None = Query(default=None),
    grade: str | None = Query(default=None),
    rarity: str | None = Query(default=None),
    trait: str | None = Query(default=None),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    in_stock: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> list[ShrimpListItemResponse]:
    return await list_shrimp_catalog_items(
        db,
        catalog_status=CatalogStatus.ACTIVE.value,
        search=search,
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


@router.get("/shrimp/slug/{slug}", response_model=ShrimpDetailResponse)
async def get_shrimp_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> ShrimpDetailResponse:
    try:
        return await get_shrimp_catalog_item_by_slug(db, slug, active_only=True)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/shrimp/{shrimp_id}", response_model=ShrimpDetailResponse)
async def get_shrimp(
    shrimp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ShrimpDetailResponse:
    try:
        return await get_shrimp_catalog_item(db, shrimp_id, active_only=True)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
