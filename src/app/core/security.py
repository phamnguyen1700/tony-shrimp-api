import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

settings = get_settings()
password_hash = PasswordHash.recommended()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_secret(secret: str) -> str:
    return password_hash.hash(secret)


def verify_secret(secret: str, secret_hash: str) -> bool:
    return password_hash.verify(secret, secret_hash)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(
    *,
    user_id: uuid.UUID,
    email: str,
    role: str,
) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def create_token_lookup_hash(token: str) -> str:
    return hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
