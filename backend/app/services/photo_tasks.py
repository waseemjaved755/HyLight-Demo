import logging
from uuid import UUID

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.redis_client import invalidate_photo_cache
from app.services.photo_service import PhotoService

logger = logging.getLogger(__name__)


async def run_photo_description_background(photo_id: UUID, owner_id: UUID) -> None:
    """Generate AI description after upload finalize (separate DB session)."""
    settings = get_settings()
    if not settings.gemini_api_key:
        logger.info("describe_background_skipped_no_gemini", extra={"photo_id": str(photo_id)})
        return

    logger.info("describe_background_started", extra={"photo_id": str(photo_id)})
    await invalidate_photo_cache(str(photo_id))
    try:
        async with AsyncSessionLocal() as session:
            service = PhotoService(session)
            await service.generate_description(
                photo_id,
                owner_id,
                image_url=None,
                retry=False,
            )
            await session.commit()
        logger.info("describe_background_finished", extra={"photo_id": str(photo_id)})
    except Exception:
        logger.exception("describe_background_failed", extra={"photo_id": str(photo_id)})
