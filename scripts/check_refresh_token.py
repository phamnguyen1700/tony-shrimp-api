import asyncio
import selectors

from app.db.session import AsyncSessionLocal
from app.services.auth import refresh_access_token


async def main() -> None:
    refresh_token = input("Enter refresh token: ").strip()

    async with AsyncSessionLocal() as db:
        auth_response, access_token, refresh_token = await refresh_access_token(
            db,
            refresh_token=refresh_token,
        )

    print(auth_response.user.email, auth_response.user.role, auth_response.user.status)
    print("Access cookie token prefix:", access_token[:24])
    print("Refresh cookie token prefix:", refresh_token[:24])


if __name__ == "__main__":
    asyncio.run(
        main(),
        loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
    )
