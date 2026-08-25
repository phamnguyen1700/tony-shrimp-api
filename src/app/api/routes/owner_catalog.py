import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, require_roles
from app.models.auth.user import User
from app.models.catalog import CatalogStatus
from app.schemas.catalog import (
    CareParameterCreate,
    CatalogOptionsResponse,
    OwnerShrimpListItemResponse,
    ShrimpCreate,
    ShrimpDetailResponse,
    ShrimpImageCreate,
    ShrimpImageUpdate,
    ShrimpUpdate,
    ShrimpVariantCreate,
    ShrimpVariantUpdate,
)
from app.schemas.upload import ImagePresignedUploadRequest, PresignedUploadResponse
from app.services.catalog import (
    add_shrimp_image,
    add_shrimp_variant,
    create_shrimp_catalog_item,
    delete_inactive_shrimp_catalog_item,
    edit_shrimp_image,
    edit_shrimp_variant,
    get_catalog_options,
    get_shrimp_catalog_item,
    list_owner_shrimp_catalog_items,
    remove_shrimp_image,
    remove_shrimp_variant,
    set_shrimp_catalog_status,
    upsert_shrimp_care_parameter,
    update_shrimp_catalog_item,
)
from app.services.catalog.owner_service import MAX_SHRIMP_IMAGES
from app.services.upload import create_presigned_upload_url

router = APIRouter(prefix="/owner/catalog", tags=["catalog - owner"])


@router.get("/options", response_model=CatalogOptionsResponse)
async def get_owner_catalog_options(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> CatalogOptionsResponse:
    return await get_catalog_options(db, active_only=False)


@router.get("/shrimp", response_model=list[OwnerShrimpListItemResponse])
async def list_owner_shrimp(
    catalog_status: CatalogStatus | None = Query(default=None),
    search: str | None = Query(default=None),
    species: str | None = Query(default=None),
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
    current_user: User = Depends(require_roles("owner", "admin")),
) -> list[OwnerShrimpListItemResponse]:
    return await list_owner_shrimp_catalog_items(
        db,
        catalog_status=catalog_status.value if catalog_status else None,
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


@router.get("/shrimp/{shrimp_id}", response_model=ShrimpDetailResponse)
async def get_owner_shrimp(
    shrimp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> ShrimpDetailResponse:
    try:
        return await get_shrimp_catalog_item(db, shrimp_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/shrimp",
    response_model=ShrimpDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_owner_shrimp(
    payload: ShrimpCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> ShrimpDetailResponse:
    try:
        return await create_shrimp_catalog_item(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/shrimp/{shrimp_id}", response_model=ShrimpDetailResponse)
async def update_owner_shrimp(
    shrimp_id: uuid.UUID,
    payload: ShrimpUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> ShrimpDetailResponse:
    try:
        return await update_shrimp_catalog_item(db, shrimp_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/shrimp/{shrimp_id}/activate", response_model=ShrimpDetailResponse)
async def activate_owner_shrimp(
    shrimp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> ShrimpDetailResponse:
    try:
        return await set_shrimp_catalog_status(db, shrimp_id, CatalogStatus.ACTIVE)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/shrimp/{shrimp_id}/deactivate", response_model=ShrimpDetailResponse)
async def deactivate_owner_shrimp(
    shrimp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> ShrimpDetailResponse:
    try:
        return await set_shrimp_catalog_status(db, shrimp_id, CatalogStatus.INACTIVE)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/shrimp/{shrimp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_owner_shrimp(
    shrimp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> None:
    try:
        await delete_inactive_shrimp_catalog_item(db, shrimp_id)
    except ValueError as exc:
        detail = str(exc).lower()
        if "inactive" in detail:
            status_code = status.HTTP_400_BAD_REQUEST
        elif "r2" in detail:
            status_code = status.HTTP_502_BAD_GATEWAY
        else:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/shrimp/{shrimp_id}/variants", response_model=ShrimpDetailResponse)
async def create_owner_variant(
    shrimp_id: uuid.UUID,
    payload: ShrimpVariantCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> ShrimpDetailResponse:
    try:
        return await add_shrimp_variant(db, shrimp_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/shrimp/{shrimp_id}/variants/{variant_id}", response_model=ShrimpDetailResponse)
async def update_owner_variant(
    shrimp_id: uuid.UUID,
    variant_id: uuid.UUID,
    payload: ShrimpVariantUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> ShrimpDetailResponse:
    try:
        return await edit_shrimp_variant(db, shrimp_id, variant_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/shrimp/{shrimp_id}/variants/{variant_id}", response_model=ShrimpDetailResponse)
async def delete_owner_variant(
    shrimp_id: uuid.UUID,
    variant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> ShrimpDetailResponse:
    try:
        return await remove_shrimp_variant(db, shrimp_id, variant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/shrimp/{shrimp_id}/care-parameter", response_model=ShrimpDetailResponse)
async def upsert_owner_care_parameter(
    shrimp_id: uuid.UUID,
    payload: CareParameterCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> ShrimpDetailResponse:
    try:
        return await upsert_shrimp_care_parameter(db, shrimp_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

@router.post("/shrimp/{shrimp_id}/images", response_model=ShrimpDetailResponse)
async def create_owner_image(
    shrimp_id: uuid.UUID,
    payload: ShrimpImageCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> ShrimpDetailResponse:
    try:
        return await add_shrimp_image(db, shrimp_id, payload)
    except ValueError as exc:
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if "at most" in str(exc)
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post(
    "/shrimp/{shrimp_id}/images/presign",
    response_model=PresignedUploadResponse,
)
async def create_owner_image_presigned_upload(
    shrimp_id: uuid.UUID,
    payload: ImagePresignedUploadRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> PresignedUploadResponse:
    try:
        shrimp = await get_shrimp_catalog_item(db, shrimp_id)
        if len(shrimp.images) >= MAX_SHRIMP_IMAGES:
            raise ValueError("Each shrimp can have at most 4 images.")

        return create_presigned_upload_url(
            folder=f"shrimp/{shrimp_id}",
            filename=payload.filename,
            content_type=payload.content_type,
            file_size_bytes=payload.file_size_bytes,
        )
    except ValueError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in str(exc).lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.patch("/shrimp/{shrimp_id}/images/{image_id}", response_model=ShrimpDetailResponse)
async def update_owner_image(
    shrimp_id: uuid.UUID,
    image_id: uuid.UUID,
    payload: ShrimpImageUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> ShrimpDetailResponse:
    try:
        return await edit_shrimp_image(db, shrimp_id, image_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/shrimp/{shrimp_id}/images/{image_id}", response_model=ShrimpDetailResponse)
async def delete_owner_image(
    shrimp_id: uuid.UUID,
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> ShrimpDetailResponse:
    try:
        return await remove_shrimp_image(db, shrimp_id, image_id)
    except ValueError as exc:
        status_code = (
            status.HTTP_502_BAD_GATEWAY
            if "r2" in str(exc).lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
