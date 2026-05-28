from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import AuthUser, decode_supabase_jwt
from app.models.user import User
from app.services.user_service import UserService

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_auth(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    token = authorization.removeprefix("Bearer ").strip()
    return decode_supabase_jwt(token)


async def get_current_user(
    session: DbSession,
    auth: Annotated[AuthUser, Depends(get_current_auth)],
) -> User:
    service = UserService(session)
    return await service.get_or_create_from_auth(auth)


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAuth = Annotated[AuthUser, Depends(get_current_auth)]
