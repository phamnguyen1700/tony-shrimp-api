import asyncio
import selectors

from app.core.redis import redis_client
from app.db.session import AsyncSessionLocal
from app.services.auth import request_otp, verify_otp_and_create_session


async def main() -> None:
    email = "phamnguyen1700@gmail.com"

    await request_otp(redis_client, email)

    code = input("Enter OTP from terminal log: ").strip()

    async with AsyncSessionLocal() as db:
        auth_response, access_token, refresh_token = (
            await verify_otp_and_create_session(
                db,
                redis_client,
                email=email,
                code=code,
                ip_address="127.0.0.1",
                user_agent="check_auth_service.py",
            )
        )

    print(auth_response.user.email, auth_response.user.role, auth_response.user.status)
    print("Access cookie token prefix:", access_token[:24])
    print("Refresh cookie token prefix:", refresh_token[:24])


if __name__ == "__main__":
    asyncio.run(
        main(),
        loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
    )
