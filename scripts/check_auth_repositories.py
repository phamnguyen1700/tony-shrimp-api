import asyncio
import selectors

from app.db.session import AsyncSessionLocal
from app.repositories.auth import get_or_create_customer_by_email


async def main() -> None:
    async with AsyncSessionLocal() as db:
        user = await get_or_create_customer_by_email(
            db,
            "test@example.com",
        )
        await db.commit()
        print(user.id, user.email, user.role)


if __name__ == "__main__":
    asyncio.run(
        main(),
        loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
    )
