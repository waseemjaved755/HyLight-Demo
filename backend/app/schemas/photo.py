from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import AppModel

AiStatus = Literal["pending", "done", "failed", "skipped"]
Visibility = Literal["private", "unlisted", "public"]


class PhotoUploadInitRequest(AppModel):
    mime_type: Literal["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"]
    size_bytes: int = Field(gt=0, le=25_000_000)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    sha256: str = Field(min_length=64, max_length=64)
    taken_at: datetime | None = None
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)

    @field_validator("sha256")
    @classmethod
    def lowercase_hex(cls, value: str) -> str:
        if not all(c in "0123456789abcdef" for c in value.lower()):
            raise ValueError("sha256 must be hexadecimal")
        return value.lower()


class PhotoUploadInitResponse(AppModel):
    photo_id: UUID
    storage_path: str
    upload_instructions: str = (
        "Upload the file to Supabase Storage at this path, then call POST /v1/photos/{id}/finalize"
    )


class PhotoResponse(AppModel):
    id: UUID
    owner_id: UUID
    storage_key_original: str
    storage_key_medium: str | None
    storage_key_thumb: str | None
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    taken_at: datetime | None
    lat: float
    lng: float
    ai_description: str | None
    ai_status: AiStatus
    visibility: Visibility
    created_at: datetime


class MapPhotoFeature(AppModel):
    id: UUID
    lat: float
    lng: float
    thumb_key: str | None


class MapPhotosResponse(AppModel):
    features: list[MapPhotoFeature]
    count: int


class PhotoListItem(AppModel):
    id: UUID
    lat: float
    lng: float
    thumb_key: str | None
    ai_description: str | None
    ai_status: AiStatus
    created_at: datetime


class PhotoListResponse(AppModel):
    photos: list[PhotoListItem]
    count: int


class PhotoDescribeRequest(AppModel):
    """Optional signed URL from the client — avoids needing a Supabase secret key."""

    image_url: str | None = Field(default=None, max_length=4096)
    retry: bool = False
