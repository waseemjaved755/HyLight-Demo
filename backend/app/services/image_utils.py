import logging
from io import BytesIO

from PIL import Image

logger = logging.getLogger(__name__)

MAX_EDGE_PX = 1536
JPEG_QUALITY = 85


def prepare_image_for_gemini(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """Downscale large camera JPEGs so Gemini free tier can process them quickly."""
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            img.thumbnail((MAX_EDGE_PX, MAX_EDGE_PX), Image.Resampling.LANCZOS)
            out = BytesIO()
            img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            compressed = out.getvalue()
        logger.info(
            "image_prepared_for_gemini",
            extra={
                "original_bytes": len(image_bytes),
                "compressed_bytes": len(compressed),
                "mime_in": mime_type,
            },
        )
        return compressed, "image/jpeg"
    except Exception:
        logger.exception("image_prepare_failed", extra={"bytes": len(image_bytes)})
        if len(image_bytes) <= 4_000_000:
            return image_bytes, mime_type
        raise
