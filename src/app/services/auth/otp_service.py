import json
import random

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.security import hash_secret, normalize_email, verify_secret

settings = get_settings()


def generate_otp_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def get_otp_key(email: str) -> str:
    return f"auth:otp:{normalize_email(email)}"


def get_otp_cooldown_key(email: str) -> str:
    return f"auth:otp:cooldown:{normalize_email(email)}"


async def create_otp(
    redis: Redis,
    email: str,
) -> str:
    normalized_email = normalize_email(email)
    cooldown_key = get_otp_cooldown_key(normalized_email)

    if await redis.exists(cooldown_key):
        raise ValueError("OTP request is on cooldown.")

    code = generate_otp_code()
    payload = {
        "code_hash": hash_secret(code),
        "attempts": 0,
    }

    await redis.set(
        get_otp_key(normalized_email),
        json.dumps(payload),
        ex=settings.otp_expire_minutes * 60,
    )
    await redis.set(
        cooldown_key,
        "1",
        ex=settings.otp_request_cooldown_seconds,
    )

    return code


async def verify_otp(
    redis: Redis,
    email: str,
    code: str,
) -> bool:
    normalized_email = normalize_email(email)
    otp_key = get_otp_key(normalized_email)

    raw_payload = await redis.get(otp_key)
    if raw_payload is None:
        return False

    payload = json.loads(raw_payload)
    attempts = int(payload.get("attempts", 0))

    if attempts >= settings.otp_max_attempts:
        await redis.delete(otp_key)
        return False

    code_hash = payload["code_hash"]
    if not verify_secret(code, code_hash):
        payload["attempts"] = attempts + 1
        ttl = await redis.ttl(otp_key)

        if ttl > 0:
            await redis.set(
                otp_key,
                json.dumps(payload),
                ex=ttl,
            )

        return False

    await redis.delete(otp_key)
    return True
