import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.models.auth import User
from app.schemas.user import (
    AddressLocalityCheckResponse,
    AddressOptionsResponse,
    AddressSuburbSuggestionsResponse,
    UpdateUserProfileRequest,
    UserAddressCreate,
    UserAddressResponse,
    UserAddressUpdate,
    UserMeResponse,
)
from app.services.user import (
    check_address_locality,
    create_current_user_address,
    delete_current_user_address,
    get_address_options,
    get_current_user_profile_response,
    list_current_user_addresses,
    set_current_user_default_address,
    suggest_address_suburbs,
    update_current_user_address,
    update_current_user_profile,
)

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/me", response_model=UserMeResponse)
async def get_user_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserMeResponse:
    return await get_current_user_profile_response(db, current_user)


@router.patch("/me", response_model=UserMeResponse)
async def update_user_me(
    payload: UpdateUserProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserMeResponse:
    return await update_current_user_profile(db, current_user, payload)


@router.get("/address-options", response_model=AddressOptionsResponse)
async def get_user_address_options(
    current_user: User = Depends(get_current_user),
) -> AddressOptionsResponse:
    return await get_address_options()


@router.get("/address-suburbs", response_model=AddressSuburbSuggestionsResponse)
async def suggest_user_address_suburbs(
    search: str = Query(min_length=2, max_length=100),
    current_user: User = Depends(get_current_user),
) -> AddressSuburbSuggestionsResponse:
    return await suggest_address_suburbs(search)


@router.get("/address-locality/check", response_model=AddressLocalityCheckResponse)
async def check_user_address_locality(
    postcode: str = Query(min_length=4, max_length=4),
    suburb: str = Query(min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
) -> AddressLocalityCheckResponse:
    return await check_address_locality(postcode=postcode, suburb=suburb)


@router.get("/addresses", response_model=list[UserAddressResponse])
async def list_user_addresses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[UserAddressResponse]:
    return await list_current_user_addresses(db, current_user.id)


@router.post(
    "/addresses",
    response_model=UserAddressResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user_address(
    payload: UserAddressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserAddressResponse:
    return await create_current_user_address(db, current_user.id, payload)


@router.patch("/addresses/{address_id}", response_model=UserAddressResponse)
async def update_user_address(
    address_id: uuid.UUID,
    payload: UserAddressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserAddressResponse:
    try:
        return await update_current_user_address(
            db,
            current_user.id,
            address_id,
            payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user_address(
    address_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await delete_current_user_address(db, current_user.id, address_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch("/addresses/{address_id}/default", response_model=UserAddressResponse)
async def set_user_default_address(
    address_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserAddressResponse:
    try:
        return await set_current_user_default_address(db, current_user.id, address_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
