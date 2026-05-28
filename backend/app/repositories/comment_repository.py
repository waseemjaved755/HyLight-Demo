from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Comment)

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
