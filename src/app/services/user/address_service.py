import uuid
import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.pii import decrypt_pii, encrypt_pii
from app.models.user import UserAddress
from app.repositories.user import (
    create_user_address,
    delete_user_address,
    get_user_address,
    list_user_addresses,
    set_user_address_as_default,
    unset_default_user_addresses,
)
from app.schemas.user import (
    AddressLocalityCheckResponse,
    AddressOptionsResponse,
    AddressSuburbSuggestion,
    AddressSuburbSuggestionsResponse,
    UserAddressCreate,
    UserAddressResponse,
    UserAddressUpdate,
)

AU_STATES = ["ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]


def normalize_state(state: str) -> str:
    return state.strip().upper()


def normalize_text(value: str) -> str:
    return value.strip()


def build_address_response(address: UserAddress) -> UserAddressResponse:
    return UserAddressResponse(
        id=address.id,
        user_id=address.user_id,
        recipient_name=address.recipient_name,
        recipient_phone=decrypt_pii(address.recipient_phone_encrypted) or "",
        address_line1=decrypt_pii(address.address_line1_encrypted) or "",
        address_line2=decrypt_pii(address.address_line2_encrypted),
        suburb=address.suburb,
        state=address.state,
        postcode=address.postcode,
        is_default=address.is_default,
        created_at=address.created_at,
        updated_at=address.updated_at,
    )


async def get_address_options() -> AddressOptionsResponse:
    return AddressOptionsResponse(states=AU_STATES, suburbs=[])


async def suggest_address_suburbs(search: str) -> AddressSuburbSuggestionsResponse:
    normalized_search = normalize_text(search)
    settings = get_settings()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                settings.australian_suburbs_lookup_suburb_url,
                params={"search": normalized_search},
            )
    except httpx.HTTPError:
        return AddressSuburbSuggestionsResponse(
            items=[],
            message="Australian Suburbs suggestion service is unavailable.",
        )

    if response.status_code in {400, 404}:
        return AddressSuburbSuggestionsResponse(
            items=[],
            message="No matching suburbs found.",
        )

    if response.status_code >= 400:
        return AddressSuburbSuggestionsResponse(
            items=[],
            message="Australian Suburbs suggestion failed.",
        )

    payload = response.json()
    if not isinstance(payload, list):
        return AddressSuburbSuggestionsResponse(
            items=[],
            message="Unexpected Australian Suburbs response.",
        )

    items: list[AddressSuburbSuggestion] = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        suburb = item.get("locality")
        postcode = item.get("postcode")
        state = item.get("state")
        if suburb and postcode and state:
            items.append(
                AddressSuburbSuggestion(
                    suburb=str(suburb).strip(),
                    state=str(state).strip().upper(),
                    postcode=str(postcode).strip(),
                )
            )

    return AddressSuburbSuggestionsResponse(items=items)


async def check_address_locality(
    *,
    postcode: str,
    suburb: str,
) -> AddressLocalityCheckResponse:
    normalized_postcode = normalize_text(postcode)
    normalized_suburb = normalize_text(suburb)
    settings = get_settings()

    if len(normalized_postcode) != 4 or not normalized_postcode.isdigit():
        return AddressLocalityCheckResponse(
            found=False,
            suburb=normalized_suburb,
            postcode=normalized_postcode,
            message="Postcode should be 4 digits.",
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                settings.australian_suburbs_validate_url,
                params={
                    "postcode": normalized_postcode,
                    "suburb": normalized_suburb,
                },
            )
    except httpx.HTTPError:
        return AddressLocalityCheckResponse(
            found=False,
            suburb=normalized_suburb,
            postcode=normalized_postcode,
            message="Australian Suburbs locality check service is unavailable.",
        )

    if response.status_code in {400, 404}:
        return AddressLocalityCheckResponse(
            found=False,
            suburb=normalized_suburb,
            postcode=normalized_postcode,
            message="Address locality not found.",
        )

    if response.status_code >= 400:
        return AddressLocalityCheckResponse(
            found=False,
            suburb=normalized_suburb,
            postcode=normalized_postcode,
            message="Australian Suburbs locality check failed.",
        )

    payload = response.json()
    found = bool(payload.get("valid", False)) if isinstance(payload, dict) else False

    return AddressLocalityCheckResponse(
        found=found,
        suburb=normalized_suburb,
        postcode=normalized_postcode,
        message=(
            "Address locality found." if found else "Address locality not found yet."
        ),
    )


async def list_current_user_addresses(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[UserAddressResponse]:
    addresses = await list_user_addresses(db, user_id)
    return [build_address_response(address) for address in addresses]


async def create_current_user_address(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: UserAddressCreate,
) -> UserAddressResponse:
    existing_addresses = await list_user_addresses(db, user_id)
    is_default = payload.is_default or not existing_addresses

    if is_default:
        await unset_default_user_addresses(db, user_id)

    address = await create_user_address(
        db,
        user_id=user_id,
        recipient_name=normalize_text(payload.recipient_name),
        recipient_phone_encrypted=encrypt_pii(payload.recipient_phone) or "",
        address_line1_encrypted=encrypt_pii(payload.address_line1) or "",
        address_line2_encrypted=encrypt_pii(payload.address_line2),
        suburb=normalize_text(payload.suburb),
        state=normalize_state(payload.state),
        postcode=normalize_text(payload.postcode),
        is_default=is_default,
    )

    await db.commit()
    await db.refresh(address)

    return build_address_response(address)


async def update_current_user_address(
    db: AsyncSession,
    user_id: uuid.UUID,
    address_id: uuid.UUID,
    payload: UserAddressUpdate,
) -> UserAddressResponse:
    address = await get_user_address(db, user_id=user_id, address_id=address_id)
    if address is None:
        raise ValueError("Address not found.")

    if "recipient_name" in payload.model_fields_set and payload.recipient_name:
        address.recipient_name = normalize_text(payload.recipient_name)

    if "recipient_phone" in payload.model_fields_set:
        address.recipient_phone_encrypted = encrypt_pii(payload.recipient_phone) or ""

    if "address_line1" in payload.model_fields_set:
        address.address_line1_encrypted = encrypt_pii(payload.address_line1) or ""

    if "address_line2" in payload.model_fields_set:
        address.address_line2_encrypted = encrypt_pii(payload.address_line2)

    if "suburb" in payload.model_fields_set and payload.suburb:
        address.suburb = normalize_text(payload.suburb)

    if "state" in payload.model_fields_set and payload.state:
        address.state = normalize_state(payload.state)

    if "postcode" in payload.model_fields_set and payload.postcode:
        address.postcode = normalize_text(payload.postcode)

    if payload.is_default is True:
        await unset_default_user_addresses(db, user_id)
        address.is_default = True
    elif payload.is_default is False:
        address.is_default = False

    await db.commit()
    await db.refresh(address)

    return build_address_response(address)


async def delete_current_user_address(
    db: AsyncSession,
    user_id: uuid.UUID,
    address_id: uuid.UUID,
) -> None:
    address = await get_user_address(db, user_id=user_id, address_id=address_id)
    if address is None:
        raise ValueError("Address not found.")

    was_default = address.is_default

    await delete_user_address(db, address)

    if was_default:
        remaining_addresses = await list_user_addresses(db, user_id)
        if remaining_addresses:
            await set_user_address_as_default(db, remaining_addresses[0])

    await db.commit()


async def set_current_user_default_address(
    db: AsyncSession,
    user_id: uuid.UUID,
    address_id: uuid.UUID,
) -> UserAddressResponse:
    address = await get_user_address(db, user_id=user_id, address_id=address_id)
    if address is None:
        raise ValueError("Address not found.")

    address = await set_user_address_as_default(db, address)

    await db.commit()
    await db.refresh(address)

    return build_address_response(address)
