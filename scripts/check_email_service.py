import asyncio

from app.services.email import send_otp_email


async def main() -> None:
    await send_otp_email(
        to_email="test@example.com",
        code="123456",
    )


if __name__ == "__main__":
    asyncio.run(main())
