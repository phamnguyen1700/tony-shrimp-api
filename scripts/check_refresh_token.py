import asyncio
import selectors

from app.db.session import AsyncSessionLocal
from app.services.auth import refresh_access_token


async def main() -> None:
    refresh_token = input("Enter refresh token: ").strip()

    async with AsyncSessionLocal() as db:
        tokens = await refresh_access_token(
            db,
            refresh_token=refresh_token,
        )

    print(tokens.token_type)
    print(tokens.access_token[:40])
    print(tokens.refresh_token[:40])


if __name__ == "__main__":
    asyncio.run(
        main(),
        loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
    )
