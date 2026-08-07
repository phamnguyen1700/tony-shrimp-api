import asyncio

from app.core.redis import redis_client
from app.services.auth import create_otp, verify_otp


async def main() -> None:
    email = "otp-test@example.com"

    code = await create_otp(redis_client, email)
    print("OTP:", code)

    invalid_result = await verify_otp(redis_client, email, "000000")
    print("Invalid:", invalid_result)

    valid_result = await verify_otp(redis_client, email, code)
    print("Valid:", valid_result)

    reused_result = await verify_otp(redis_client, email, code)
    print("Reused:", reused_result)


if __name__ == "__main__":
    asyncio.run(main())
