from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


@lru_cache
def get_pii_cipher() -> Fernet:
    settings = get_settings()
    if not settings.pii_encryption_key:
        raise RuntimeError("PII_ENCRYPTION_KEY is not configured.")

    return Fernet(settings.pii_encryption_key.encode("utf-8"))


def encrypt_pii(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()
    if not normalized_value:
        return None

    return get_pii_cipher().encrypt(normalized_value.encode("utf-8")).decode("utf-8")


def decrypt_pii(value: str | None) -> str | None:
    if value is None:
        return None

    try:
        return get_pii_cipher().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted PII value.") from exc
