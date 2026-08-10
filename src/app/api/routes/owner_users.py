import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, require_roles
from app.models.auth import User, UserRole, UserStatus
from app.schemas.user import (
    OwnerUserDetailResponse,
    OwnerUserListResponse,
    UpdateUserRoleRequest,
)
from app.services.user import (
    activate_owner_user,
    deactivate_owner_user,
    delete_inactive_owner_user,
    get_owner_user_detail,
    list_owner_users,
    update_owner_user_role,
)

router = APIRouter(prefix="/owner/users", tags=["users - owner"])


def map_user_management_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    detail = str(exc)
    status_code = status.HTTP_404_NOT_FOUND
    if "your own" in detail.lower() or "inactive" in detail.lower():
        status_code = status.HTTP_400_BAD_REQUEST

    return HTTPException(status_code=status_code, detail=detail)


@router.get("", response_model=OwnerUserListResponse)
async def list_owner_user_accounts(
    search: str | None = Query(default=None),
    role: UserRole | None = Query(default=None),
    user_status: UserStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> OwnerUserListResponse:
    return await list_owner_users(
        db,
        actor=current_user,
        search=search,
        role=role,
        status=user_status,
        limit=limit,
        offset=offset,
    )


@router.get("/{user_id}", response_model=OwnerUserDetailResponse)
async def get_owner_user_account(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> OwnerUserDetailResponse:
    try:
        return await get_owner_user_detail(db, actor=current_user, user_id=user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{user_id}/activate", response_model=OwnerUserDetailResponse)
async def activate_owner_user_account(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> OwnerUserDetailResponse:
    try:
        return await activate_owner_user(db, actor=current_user, user_id=user_id)
    except (PermissionError, ValueError) as exc:
        raise map_user_management_error(exc) from exc


@router.patch("/{user_id}/deactivate", response_model=OwnerUserDetailResponse)
async def deactivate_owner_user_account(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> OwnerUserDetailResponse:
    try:
        return await deactivate_owner_user(db, actor=current_user, user_id=user_id)
    except (PermissionError, ValueError) as exc:
        raise map_user_management_error(exc) from exc


@router.patch("/{user_id}/role", response_model=OwnerUserDetailResponse)
async def update_owner_user_account_role(
    user_id: uuid.UUID,
    payload: UpdateUserRoleRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("admin")),
) -> OwnerUserDetailResponse:
    try:
        return await update_owner_user_role(
            db,
            actor=current_user,
            user_id=user_id,
            role=payload.role,
        )
    except ValueError as exc:
        raise map_user_management_error(exc) from exc


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_owner_user_account(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> None:
    try:
        await delete_inactive_owner_user(db, actor=current_user, user_id=user_id)
    except (PermissionError, ValueError) as exc:
        raise map_user_management_error(exc) from exc
