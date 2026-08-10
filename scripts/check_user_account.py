import asyncio
import selectors

from app.core.redis import redis_client
from app.db.session import AsyncSessionLocal
from app.models.auth import User
from app.services.auth import request_otp, verify_otp_and_create_session
from app.services.user import (
    create_current_user_address,
    delete_current_user_address,
    get_current_user_profile_response,
    list_current_user_addresses,
    set_current_user_default_address,
    update_current_user_profile,
)
from app.schemas.user import UpdateUserProfileRequest, UserAddressCreate


async def main() -> None:
    email = "account-test@example.com"

    await request_otp(redis_client, email)
    code = input("Enter OTP from terminal log: ").strip()

    async with AsyncSessionLocal() as db:
        auth_response, access_token, _refresh_token = await verify_otp_and_create_session(
            db,
            redis_client,
            email=email,
            code=code,
            ip_address="127.0.0.1",
            user_agent="check_user_account.py",
        )

        print("User:", auth_response.user.email, auth_response.user.role)
        print("Access cookie token prefix:", access_token[:24])

        user_result = await db.execute(
            User.__table__.select().where(User.email == email)
        )
        user_row = user_result.first()
        if user_row is None:
            raise RuntimeError("Test user was not created.")

        user = await db.get(User, user_row.id)
        if user is None:
            raise RuntimeError("Test user was not loaded.")

        me = await get_current_user_profile_response(db, user)
        print("Initial profile:", me.model_dump())

        me = await update_current_user_profile(
            db,
            user,
            UpdateUserProfileRequest(
                full_name="Tony Account Test",
                phone="0400000000",
            ),
        )
        print("Updated profile:", me.model_dump())

        address_1 = await create_current_user_address(
            db,
            user.id,
            UserAddressCreate(
                recipient_name="Tony Nguyen",
                recipient_phone="0400000001",
                address_line1="12 George Street",
                address_line2=None,
                suburb="Richmond",
                state="VIC",
                postcode="3121",
            ),
        )
        print("Address 1:", address_1.model_dump())

        address_2 = await create_current_user_address(
            db,
            user.id,
            UserAddressCreate(
                recipient_name="Tony Nguyen",
                recipient_phone="0400000002",
                address_line1="88 Victoria Road",
                address_line2="Shop 3",
                suburb="Parramatta",
                state="NSW",
                postcode="2150",
                is_default=True,
            ),
        )
        print("Address 2:", address_2.model_dump())

        addresses = await list_current_user_addresses(db, user.id)
        print("After create:")
        for address in addresses:
            print(address.id, address.is_default, address.address_line1)

        default_address = await set_current_user_default_address(
            db,
            user.id,
            address_2.id,
        )
        print("Set default:", default_address.id, default_address.is_default)

        await delete_current_user_address(db, user.id, address_2.id)

        addresses = await list_current_user_addresses(db, user.id)
        print("After deleting previous default:")
        for address in addresses:
            print(address.id, address.is_default, address.address_line1)


if __name__ == "__main__":
    asyncio.run(
        main(),
        loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
    )
