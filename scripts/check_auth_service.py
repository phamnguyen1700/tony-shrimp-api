import asyncio
import selectors

from app.core.redis import redis_client
from app.db.session import AsyncSessionLocal
from app.services.auth import request_otp, verify_otp_and_create_session


async def main() -> None:
    email = "auth-service-test@example.com"

    await request_otp(redis_client, email)

    code = input("Enter OTP from terminal log: ").strip()

    async with AsyncSessionLocal() as db:
        tokens = await verify_otp_and_create_session(
            db,
            redis_client,
            email=email,
            code=code,
            ip_address="127.0.0.1",
            user_agent="check_auth_service.py",
        )

    print(tokens.token_type)
    print(tokens.access_token[:40])
    print(tokens.refresh_token[:40])


if __name__ == "__main__":
    asyncio.run(
        main(),
        loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
    )
