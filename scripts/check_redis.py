import asyncio

from app.core.redis import redis_client


async def main() -> None:
    pong = await redis_client.ping()
    print(f"Redis ping response: {pong}")


if __name__ == "__main__":
    asyncio.run(main())
