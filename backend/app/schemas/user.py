from datetime import datetime
from uuid import UUID

from app.schemas.common import AppModel


class UserResponse(AppModel):
    id: UUID
    email: str
    display_name: str
    avatar_url: str | None
    created_at: datetime
