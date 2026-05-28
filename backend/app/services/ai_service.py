import base64
import logging

import httpx

from app.core.config import get_settings
from app.services.image_utils import prepare_image_for_gemini

logger = logging.getLogger(__name__)


async def generate_photo_description(
    *,
    image_bytes: bytes,
    mime_type: str,
) -> str | None:
    settings = get_settings()
    if not settings.gemini_api_key:
        return None

    try:
        image_bytes, mime_type = prepare_image_for_gemini(image_bytes, mime_type)
    except Exception:
        return None

    b64 = base64.b64encode(image_bytes).decode("ascii")
    logger.info("gemini_request_start", extra={"model": settings.gemini_model, "bytes": len(image_bytes)})
    model = settings.gemini_model
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={settings.gemini_api_key}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Describe this photograph in exactly two sentences "
                            "that would be useful for people to know about the photo. Be specific about what is visible."
                        )
                    },
                    {"inline_data": {"mime_type": mime_type, "data": b64}},
                ]
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 429:
                logger.error(
                    "gemini_rate_limited",
                    extra={"model": model, "detail": response.text[:300]},
                )
                return None
            response.raise_for_status()
            data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            logger.error("gemini_empty_candidates", extra={"model": model, "data": data})
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        text = parts[0].get("text", "").strip() if parts else ""
        return text or None
    except httpx.HTTPStatusError as exc:
        logger.error(
            "gemini_http_error",
            extra={
                "model": model,
                "status": exc.response.status_code,
                "detail": exc.response.text[:300],
            },
        )
        return None
    except Exception:
        logger.exception("gemini_description_failed", extra={"model": model})
        return None


async def download_from_signed_url(image_url: str) -> tuple[bytes, str] | None:
    settings = get_settings()
    if settings.supabase_url:
        allowed_host = settings.supabase_url.replace("https://", "").replace("http://", "").rstrip("/")
        if allowed_host not in image_url:
            logger.warning("signed_url_host_mismatch", extra={"url": image_url[:80]})
            return None

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            mime = response.headers.get("content-type", "image/jpeg")
            return response.content, mime
    except Exception:
        logger.exception("signed_url_download_failed")
        return None


async def download_from_supabase_storage(storage_path: str) -> tuple[bytes, str] | None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None

    bucket = settings.storage_bucket
    object_url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{storage_path}"

    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(object_url, headers=headers)
            response.raise_for_status()
            mime = response.headers.get("content-type", "image/jpeg")
            return response.content, mime
    except Exception:
        logger.exception("storage_download_failed", extra={"path": storage_path})
        return None
