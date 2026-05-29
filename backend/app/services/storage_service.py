import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _service_role_headers() -> dict[str, str] | None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    return {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }


def _object_url(storage_path: str) -> str | None:
    settings = get_settings()
    if not settings.supabase_url:
        return None
    bucket = settings.storage_bucket
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{storage_path}"


async def download_storage_object(storage_path: str) -> tuple[bytes, str] | None:
    headers = _service_role_headers()
    object_url = _object_url(storage_path)
    if not headers or not object_url:
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(object_url, headers=headers)
            response.raise_for_status()
            mime = response.headers.get("content-type", "image/jpeg")
            return response.content, mime
    except Exception:
        logger.exception("storage_download_failed", extra={"path": storage_path})
        return None


async def delete_storage_object(storage_path: str) -> bool:
    headers = _service_role_headers()
    object_url = _object_url(storage_path)
    if not headers or not object_url:
        logger.warning("storage_delete_skipped", extra={"reason": "missing_supabase_credentials"})
        return False

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(object_url, headers=headers)
            if response.status_code in (200, 204, 404):
                return True
            logger.warning(
                "storage_delete_failed",
                extra={"path": storage_path, "status": response.status_code},
            )
            return False
    except Exception:
        logger.exception("storage_delete_error", extra={"path": storage_path})
        return False
