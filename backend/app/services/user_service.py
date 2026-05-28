from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthUser
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._users = UserRepository(session)

    async def get_or_create_from_auth(self, auth: AuthUser) -> User:
        existing = await self._users.get_by_supabase_id(auth.id)
        if existing:
            return existing

        email = auth.email or f"{auth.id}@users.local"
        display_name = email.split("@")[0]

        user = User(
            supabase_user_id=auth.id,
            email=email,
            display_name=display_name,
        )
        return await self._users.add(user)

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self._users.get_by_id(user_id)
