import pytest
from pydantic import ValidationError

from app.schemas.user import UpdateUserProfileRequest, UserAddressCreate


def test_user_address_create_accepts_minimum_delivery_address() -> None:
    address = UserAddressCreate(
        recipient_name="Nguyen Pham",
        recipient_phone="+61 400 000 000",
        address_line1="1 Grants Rd",
        suburb="Melbourne Airport",
        state="VIC",
        postcode="3045",
    )

    assert address.address_line2 is None
    assert not address.is_default


@pytest.mark.parametrize(
    "field_name",
    ["recipient_name", "recipient_phone", "address_line1", "suburb", "state", "postcode"],
)
def test_user_address_create_rejects_blank_required_fields(field_name: str) -> None:
    payload = {
        "recipient_name": "Nguyen Pham",
        "recipient_phone": "+61 400 000 000",
        "address_line1": "1 Grants Rd",
        "suburb": "Melbourne Airport",
        "state": "VIC",
        "postcode": "3045",
    }
    payload[field_name] = ""

    with pytest.raises(ValidationError):
        UserAddressCreate(**payload)


def test_profile_update_allows_partial_payload() -> None:
    profile = UpdateUserProfileRequest(full_name="Tony Shrimp")

    assert profile.full_name == "Tony Shrimp"
    assert profile.phone is None
