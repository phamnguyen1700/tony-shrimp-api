import uuid

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_secret,
    normalize_email,
    verify_secret,
)


def main() -> None:
    email = normalize_email(" Test@Example.COM ")
    print(email)

    refresh_token = create_refresh_token()
    refresh_token_hash = hash_secret(refresh_token)
    print(verify_secret(refresh_token, refresh_token_hash))

    access_token = create_access_token(
        user_id=uuid.uuid4(),
        email=email,
        role="customer",
    )
    payload = decode_access_token(access_token)
    print(payload["email"], payload["role"])


if __name__ == "__main__":
    main()
