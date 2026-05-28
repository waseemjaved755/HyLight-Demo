from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import AppModel


class CommentCreateRequest(AppModel):
    body: str = Field(min_length=1, max_length=2000)


class CommentResponse(AppModel):
    id: UUID
    photo_id: UUID
    author_id: UUID
    body: str
    created_at: datetime
