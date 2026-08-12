import asyncio

from app.services.email import send_otp_email


async def main() -> None:
    await send_otp_email(
        to_email="phamnguyen1700@gmail.com",
        code="123456",
    )
    print("Sent test OTP email to phamnguyen1700@gmail.com")


if __name__ == "__main__":
    asyncio.run(main())
