import uuid

from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_token_lookup_hash,
    decode_access_token,
    hash_secret,
    normalize_email,
    verify_secret,
)


def test_normalize_email_strips_and_lowercases() -> None:
    assert normalize_email("  Test.User@Example.COM  ") == "test.user@example.com"


def test_hash_secret_verifies_original_secret_only() -> None:
    secret_hash = hash_secret("123456")

    assert verify_secret("123456", secret_hash)
    assert not verify_secret("654321", secret_hash)


def test_create_access_token_round_trip() -> None:
    user_id = uuid.uuid4()

    token = create_access_token(
        user_id=user_id,
        email="customer@example.com",
        role="customer",
    )
    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["email"] == "customer@example.com"
    assert payload["role"] == "customer"


def test_refresh_token_and_lookup_hash_shape() -> None:
    token = create_refresh_token()
    lookup_hash = create_token_lookup_hash(token)

    assert len(token) > 40
    assert len(lookup_hash) == 64
    assert create_token_lookup_hash(token) == lookup_hash
    assert create_token_lookup_hash(token + "x") != lookup_hash
