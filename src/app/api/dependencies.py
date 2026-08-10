import uuid
from collections.abc import AsyncGenerator, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.core.security import decode_access_token
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.auth.user import User, UserStatus
from app.repositories.auth import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)
settings = get_settings()


async def get_redis_client() -> AsyncGenerator[Redis, None]:
    yield redis_client


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    token = request.cookies.get(settings.access_token_cookie_name)
    if token is None and credentials is not None:
        token = credentials.credentials

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload["sub"]))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from exc

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user


def require_roles(*roles: str) -> Callable[..., User]:
    async def dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )

        return current_user

    return dependency


__all__ = [
    "AsyncSession",
    "Redis",
    "get_current_user",
    "get_db_session",
    "get_redis_client",
    "require_roles",
]
