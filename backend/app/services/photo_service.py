import json
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.config import get_settings
from app.core.redis_client import (
    cache_get,
    cache_setex,
    invalidate_comments_cache,
    invalidate_map_cache,
    invalidate_photo_cache,
    is_redis_available,
)
from app.models.photo import Photo
from app.models.user import User
from app.repositories.comment_repository import CommentRepository
from app.repositories.photo_repository import PhotoRepository
from app.services.storage_service import delete_storage_object
from app.services.ai_service import (
    download_from_signed_url,
    download_from_supabase_storage,
    generate_photo_description,
)
from app.schemas.photo import (
    MapPhotoFeature,
    MapPhotosResponse,
    PhotoListItem,
    PhotoListResponse,
    PhotoResponse,
    PhotoUploadInitRequest,
    PhotoUploadInitResponse,
)


PHOTO_CACHE_TTL_SECONDS = 600


class PhotoService:
    def __init__(self, session: AsyncSession) -> None:
        self._photos = PhotoRepository(session)
        self._comments = CommentRepository(session)

    @staticmethod
    def _photo_cache_key(photo_id: UUID) -> str:
        return f"photo:{photo_id}"

    async def _write_photo_cache(self, photo_id: UUID, response: PhotoResponse) -> None:
        await cache_setex(
            self._photo_cache_key(photo_id),
            PHOTO_CACHE_TTL_SECONDS,
            response.model_dump_json(),
        )

    async def _photo_response_cached_or_db(self, photo_id: UUID, photo: Photo) -> PhotoResponse:
        cached = await cache_get(self._photo_cache_key(photo_id))
        if cached:
            return PhotoResponse.model_validate_json(cached)
        response = await self._to_response(photo)
        if is_redis_available():
            await self._write_photo_cache(photo_id, response)
        return response

    async def init_upload(
        self,
        *,
        owner: User,
        payload: PhotoUploadInitRequest,
    ) -> PhotoUploadInitResponse:
        # Storage path must start with Supabase auth user id (auth.uid()) for RLS policies
        owner_folder = str(owner.supabase_user_id)
        placeholder_path = f"{owner_folder}/{uuid4()}/original"
        photo = await self._photos.create_pending(
            owner_id=owner.id,
            storage_key_original=placeholder_path,
            mime_type=payload.mime_type,
            size_bytes=payload.size_bytes,
            lng=payload.lng,
            lat=payload.lat,
            width=payload.width,
            height=payload.height,
            taken_at=payload.taken_at,
        )
        storage_path = f"{owner_folder}/{photo.id}/original"
        photo.storage_key_original = storage_path
        return PhotoUploadInitResponse(photo_id=photo.id, storage_path=storage_path)

    async def _require_owned_photo(self, photo_id: UUID, owner_id: UUID) -> Photo:
        photo = await self._photos.get_active(photo_id)
        if photo is None or photo.owner_id != owner_id:
            raise ValueError("Photo not found")
        return photo

    async def finalize(self, photo_id: UUID, owner_id: UUID) -> PhotoResponse:
        photo = await self._require_owned_photo(photo_id, owner_id)
        await invalidate_map_cache()
        await invalidate_photo_cache(str(photo_id))
        response = await self._to_response(photo)
        # Do not cache yet — background AI task will cache when description is ready
        return response

    async def get_photo(self, photo_id: UUID) -> tuple[PhotoResponse | None, str]:
        """Returns (photo, cache_source) where cache_source is hit | miss | disabled."""
        cache_key = self._photo_cache_key(photo_id)
        cached = await cache_get(cache_key)
        if cached:
            logger.info("photo_cache_hit", extra={"photo_id": str(photo_id)})
            return PhotoResponse.model_validate_json(cached), "hit"

        photo = await self._photos.get_active(photo_id)
        if photo is None:
            return None, "miss"

        response = await self._to_response(photo)
        if is_redis_available():
            await self._write_photo_cache(photo_id, response)
            logger.info("photo_cache_miss_stored", extra={"photo_id": str(photo_id)})
            return response, "miss"

        logger.info("photo_db_only_redis_off", extra={"photo_id": str(photo_id)})
        return response, "disabled"

    async def generate_description(
        self,
        photo_id: UUID,
        owner_id: UUID,
        *,
        image_url: str | None = None,
        retry: bool = False,
    ) -> PhotoResponse:
        photo = await self._require_owned_photo(photo_id, owner_id)

        logger.info(
            "describe_photo",
            extra={
                "photo_id": str(photo_id),
                "ai_status": photo.ai_status,
                "has_description": bool(photo.ai_description),
                "retry": retry,
            },
        )

        if photo.ai_status == "done" and photo.ai_description:
            logger.info("describe_skip_already_done", extra={"photo_id": str(photo_id)})
            return await self._photo_response_cached_or_db(photo_id, photo)

        if photo.ai_status == "failed" and not retry:
            logger.info("describe_skip_failed_use_retry", extra={"photo_id": str(photo_id)})
            return await self._photo_response_cached_or_db(photo_id, photo)

        if photo.ai_status == "failed" and retry:
            await self._photos.set_ai_status(photo_id, status="pending")

        settings = get_settings()
        if not settings.gemini_api_key:
            await self._photos.set_ai_status(photo_id, status="skipped")
            photo = await self._photos.get_active(photo_id)
            assert photo is not None
            return await self._to_response(photo)

        downloaded = None
        if image_url:
            downloaded = await download_from_signed_url(image_url)
        if downloaded is None:
            downloaded = await download_from_supabase_storage(photo.storage_key_original)
        if downloaded is None:
            logger.error("describe_download_failed", extra={"photo_id": str(photo_id)})
            await self._photos.set_ai_status(photo_id, status="failed")
            photo = await self._photos.get_active(photo_id)
            assert photo is not None
            return await self._to_response(photo)

        image_bytes, mime_type = downloaded
        logger.info(
            "describe_download_ok",
            extra={"photo_id": str(photo_id), "bytes": len(image_bytes), "mime": mime_type},
        )
        description = await generate_photo_description(
            image_bytes=image_bytes,
            mime_type=mime_type,
        )

        if description:
            await self._photos.set_ai_result(photo_id, description=description, status="done")
            logger.info(
                "describe_saved_to_db",
                extra={"photo_id": str(photo_id), "chars": len(description)},
            )
        else:
            logger.error("describe_gemini_failed", extra={"photo_id": str(photo_id)})
            await self._photos.set_ai_status(photo_id, status="failed")

        photo = await self._photos.get_active(photo_id)
        assert photo is not None
        if photo.ai_status == "failed":
            await invalidate_photo_cache(str(photo_id))
            return await self._to_response(photo)
        return await self._photo_response_cached_or_db(photo_id, photo)

    async def map_photos(
        self,
        *,
        min_lng: float,
        min_lat: float,
        max_lng: float,
        max_lat: float,
        viewer_id: UUID | None,
    ) -> MapPhotosResponse:
        cache_key = self._cache_key(min_lng, min_lat, max_lng, max_lat, viewer_id)
        cached = await cache_get(cache_key)
        if cached:
            data = json.loads(cached)
            return MapPhotosResponse.model_validate(data)

        photos = await self._photos.list_in_bbox(
            min_lng=min_lng,
            min_lat=min_lat,
            max_lng=max_lng,
            max_lat=max_lat,
            owner_id=viewer_id,
        )
        features: list[MapPhotoFeature] = []
        for photo in photos:
            features.append(await self._to_map_feature(photo))
        response = MapPhotosResponse(features=features, count=len(features))
        await cache_setex(cache_key, 60, response.model_dump_json())
        return response

    async def list_for_owner(self, owner_id: UUID) -> PhotoListResponse:
        photos = await self._photos.list_by_owner(owner_id)
        items: list[PhotoListItem] = []
        for photo in photos:
            lng, lat = await self._extract_lat_lng(photo)
            items.append(
                PhotoListItem(
                    id=photo.id,
                    lat=lat,
                    lng=lng,
                    thumb_key=photo.storage_key_thumb or photo.storage_key_original,
                    ai_description=photo.ai_description,
                    ai_status=photo.ai_status,  # type: ignore[arg-type]
                    created_at=photo.created_at,
                )
            )
        return PhotoListResponse(photos=items, count=len(items))

    async def delete_photo(self, photo_id: UUID, owner_id: UUID) -> None:
        photo = await self._require_owned_photo(photo_id, owner_id)

        now = datetime.now(timezone.utc)
        photo.deleted_at = now
        await self._comments.soft_delete_for_photo(photo_id, now)

        storage_paths = [photo.storage_key_original]
        if photo.storage_key_medium:
            storage_paths.append(photo.storage_key_medium)
        if photo.storage_key_thumb:
            storage_paths.append(photo.storage_key_thumb)
        for path in storage_paths:
            await delete_storage_object(path)

        await invalidate_map_cache()
        await invalidate_photo_cache(str(photo_id))
        await invalidate_comments_cache(str(photo_id))

    async def _to_map_feature(self, photo: Photo) -> MapPhotoFeature:
        lng, lat = await self._extract_lat_lng(photo)
        return MapPhotoFeature(
            id=photo.id,
            lat=lat,
            lng=lng,
            thumb_key=photo.storage_key_thumb or photo.storage_key_original,
        )

    async def _to_response(self, photo: Photo) -> PhotoResponse:
        lng, lat = await self._extract_lat_lng(photo)
        return PhotoResponse(
            id=photo.id,
            owner_id=photo.owner_id,
            storage_key_original=photo.storage_key_original,
            storage_key_medium=photo.storage_key_medium,
            storage_key_thumb=photo.storage_key_thumb,
            mime_type=photo.mime_type,
            size_bytes=photo.size_bytes,
            width=photo.width,
            height=photo.height,
            taken_at=photo.taken_at,
            lat=lat,
            lng=lng,
            ai_description=photo.ai_description,
            ai_status=photo.ai_status,  # type: ignore[arg-type]
            visibility=photo.visibility,  # type: ignore[arg-type]
            created_at=photo.created_at,
        )

    async def _extract_lat_lng(self, photo: Photo) -> tuple[float, float]:
        coords = await self._photos.get_coordinates(photo.id)
        if coords is None:
            return 0.0, 0.0
        return coords

    @staticmethod
    def _cache_key(
        min_lng: float,
        min_lat: float,
        max_lng: float,
        max_lat: float,
        viewer_id: UUID | None,
    ) -> str:
        viewer = str(viewer_id) if viewer_id else "anon"
        return f"map:{min_lng:.4f}:{min_lat:.4f}:{max_lng:.4f}:{max_lat:.4f}:{viewer}"

