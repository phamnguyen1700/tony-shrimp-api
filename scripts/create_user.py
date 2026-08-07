import argparse
import asyncio
import selectors

from app.core.security import normalize_email
from app.db.session import AsyncSessionLocal
from app.models.auth.user import UserRole
from app.repositories.auth import create_user, get_user_by_email


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update a local user.")
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--role",
        choices=[role.value for role in UserRole],
        default=UserRole.CUSTOMER.value,
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    email = normalize_email(args.email)
    role = UserRole(args.role)

    async with AsyncSessionLocal() as db:
        user = await get_user_by_email(db, email)
        if user is None:
            user = await create_user(db, email=email, role=role)
            action = "created"
        else:
            user.role = role.value
            await db.flush()
            action = "updated"

        await db.commit()
        print(f"{action}: {user.id} {user.email} {user.role}")


if __name__ == "__main__":
    asyncio.run(
        main(),
        loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
    )
