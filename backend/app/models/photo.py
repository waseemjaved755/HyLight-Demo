import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    storage_key_original: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key_medium: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_key_thumb: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[Any] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    altitude_m: Mapped[float | None] = mapped_column(nullable=True)

    ai_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    ai_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)

    exif: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), default="private", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="photos")
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="photo")
