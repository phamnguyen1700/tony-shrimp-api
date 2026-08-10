from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pii import decrypt_pii, encrypt_pii
from app.models.auth import User
from app.repositories.user import get_or_create_user_profile, update_user_profile
from app.schemas.user import UpdateUserProfileRequest, UserMeResponse


def build_user_me_response(user: User, phone: str | None) -> UserMeResponse:
    profile = user.profile

    return UserMeResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        full_name=profile.full_name if profile else None,
        phone=phone,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def get_current_user_profile_response(
    db: AsyncSession,
    user: User,
) -> UserMeResponse:
    profile = await get_or_create_user_profile(db, user.id)
    await db.commit()
    await db.refresh(profile)
    await db.refresh(user, attribute_names=["profile"])

    return build_user_me_response(
        user,
        phone=decrypt_pii(profile.phone_encrypted),
    )


async def update_current_user_profile(
    db: AsyncSession,
    user: User,
    payload: UpdateUserProfileRequest,
) -> UserMeResponse:
    profile = await get_or_create_user_profile(db, user.id)

    full_name = profile.full_name
    phone_encrypted = profile.phone_encrypted

    if "full_name" in payload.model_fields_set:
        full_name = payload.full_name.strip() if payload.full_name else None

    if "phone" in payload.model_fields_set:
        phone_encrypted = encrypt_pii(payload.phone)

    profile = await update_user_profile(
        db,
        profile,
        full_name=full_name,
        phone_encrypted=phone_encrypted,
    )

    await db.commit()
    await db.refresh(profile)
    await db.refresh(user, attribute_names=["profile"])

    return build_user_me_response(
        user,
        phone=decrypt_pii(profile.phone_encrypted),
    )
