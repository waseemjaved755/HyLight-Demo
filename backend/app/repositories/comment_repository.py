from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Comment)

    async def get_active(self, comment_id: UUID) -> Comment | None:
        stmt = select(Comment).where(Comment.id == comment_id, Comment.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_photo(
        self,
        photo_id: UUID,
        *,
        limit: int = 50,
        after_id: UUID | None = None,
    ) -> list[Comment]:
        stmt = (
            select(Comment)
            .where(Comment.photo_id == photo_id, Comment.deleted_at.is_(None))
            .order_by(Comment.created_at.desc())
            .limit(limit)
        )
        if after_id is not None:
            stmt = stmt.where(Comment.id < after_id)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete_for_photo(self, photo_id: UUID, deleted_at: datetime) -> None:
        stmt = (
            update(Comment)
            .where(Comment.photo_id == photo_id, Comment.deleted_at.is_(None))
            .values(deleted_at=deleted_at)
        )
        await self._session.execute(stmt)
