import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserAddressCreate(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=255)
    recipient_phone: str = Field(min_length=1, max_length=32)
    address_line1: str = Field(min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    suburb: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=50)
    postcode: str = Field(min_length=1, max_length=16)
    is_default: bool = False


class UserAddressUpdate(BaseModel):
    recipient_name: str | None = Field(default=None, min_length=1, max_length=255)
    recipient_phone: str | None = Field(default=None, min_length=1, max_length=32)
    address_line1: str | None = Field(default=None, min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    suburb: str | None = Field(default=None, min_length=1, max_length=100)
    state: str | None = Field(default=None, min_length=1, max_length=50)
    postcode: str | None = Field(default=None, min_length=1, max_length=16)
    is_default: bool | None = None


class UserAddressResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    recipient_name: str
    recipient_phone: str
    address_line1: str
    address_line2: str | None
    suburb: str
    state: str
    postcode: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class AddressOptionsResponse(BaseModel):
    states: list[str]
    suburbs: list[str] = []


class AddressSuburbSuggestion(BaseModel):
    suburb: str
    state: str
    postcode: str


class AddressSuburbSuggestionsResponse(BaseModel):
    items: list[AddressSuburbSuggestion]
    source: str = "australian_suburbs"
    message: str | None = None


class AddressLocalityCheckResponse(BaseModel):
    found: bool
    suburb: str
    postcode: str
    source: str = "australian_suburbs"
    message: str | None = None
