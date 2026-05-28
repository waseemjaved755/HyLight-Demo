import json
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import (
    cache_get,
    cache_setex,
    invalidate_comments_cache,
    is_redis_available,
)
from app.models.comment import Comment
from app.models.user import User
from app.repositories.comment_repository import CommentRepository
from app.repositories.photo_repository import PhotoRepository
from app.schemas.comment import CommentCreateRequest, CommentResponse

logger = logging.getLogger(__name__)

COMMENTS_CACHE_TTL_SECONDS = 300


class CommentService:
    def __init__(self, session: AsyncSession) -> None:
        self._comments = CommentRepository(session)
        self._photos = PhotoRepository(session)

    @staticmethod
    def _comments_cache_key(photo_id: UUID) -> str:
        return f"comments:{photo_id}"

    async def create(
        self,
        *,
        photo_id: UUID,
        author: User,
        payload: CommentCreateRequest,
    ) -> CommentResponse:
        photo = await self._photos.get_active(photo_id)
        if photo is None:
            raise ValueError("Photo not found")

        comment = Comment(
            photo_id=photo_id,
            author_id=author.id,
            body=payload.body,
        )
        saved = await self._comments.add(comment)
        await invalidate_comments_cache(str(photo_id))
        return CommentResponse(
            id=saved.id,
            photo_id=saved.photo_id,
            author_id=saved.author_id,
            body=saved.body,
            created_at=saved.created_at,
        )

    async def list_for_photo(self, photo_id: UUID) -> tuple[list[CommentResponse], str]:
        cache_key = self._comments_cache_key(photo_id)
        cached = await cache_get(cache_key)
        if cached:
            logger.info("comments_cache_hit", extra={"photo_id": str(photo_id)})
            items = [CommentResponse.model_validate(item) for item in json.loads(cached)]
            return items, "hit"

        comments = await self._comments.list_for_photo(photo_id)
        result = [
            CommentResponse(
                id=c.id,
                photo_id=c.photo_id,
                author_id=c.author_id,
                body=c.body,
                created_at=c.created_at,
            )
            for c in comments
        ]

        if is_redis_available():
            payload = json.dumps([item.model_dump(mode="json") for item in result])
            await cache_setex(cache_key, COMMENTS_CACHE_TTL_SECONDS, payload)
            logger.info("comments_cache_miss_stored", extra={"photo_id": str(photo_id)})
            return result, "miss"

        logger.info("comments_db_only_redis_off", extra={"photo_id": str(photo_id)})
        return result, "disabled"
