from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_supabase_id(self, supabase_user_id: UUID) -> User | None:
        stmt = select(User).where(
            User.supabase_user_id == supabase_user_id,
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
