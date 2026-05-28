from datetime import datetime
from uuid import UUID

from geoalchemy2.elements import WKTElement
from geoalchemy2.types import Geometry
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.photo import Photo
from app.repositories.base import BaseRepository


class PhotoRepository(BaseRepository[Photo]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Photo)

    async def get_active(self, photo_id: UUID) -> Photo | None:
        stmt = select(Photo).where(Photo.id == photo_id, Photo.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_in_bbox(
        self,
        *,
        min_lng: float,
        min_lat: float,
        max_lng: float,
        max_lat: float,
        owner_id: UUID | None,
        limit: int = 500,
    ) -> list[Photo]:
        envelope = func.ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)
        stmt = (
            select(Photo)
            .where(
                Photo.deleted_at.is_(None),
                Photo.location.op("&&")(envelope),
            )
            .limit(limit)
        )
        if owner_id is not None:
            stmt = stmt.where(
                (Photo.owner_id == owner_id) | (Photo.visibility == "public")
            )
        else:
            stmt = stmt.where(Photo.visibility == "public")

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def set_ai_status(self, photo_id: UUID, *, status: str) -> None:
        photo = await self.get_active(photo_id)
        if photo is None:
            return
        photo.ai_status = status
        await self._session.flush()

    async def set_ai_result(
        self,
        photo_id: UUID,
        *,
        description: str,
        status: str = "done",
    ) -> None:
        photo = await self.get_active(photo_id)
        if photo is None:
            return
        photo.ai_description = description
        photo.ai_status = status
        await self._session.flush()

    async def get_coordinates(self, photo_id: UUID) -> tuple[float, float] | None:
        # ST_X/ST_Y need geometry; cast geography → geometry (works on all PostGIS versions)
        location_geom = cast(
            Photo.location,
            Geometry(geometry_type="POINT", srid=4326),
        )
        stmt = select(
            func.ST_Y(location_geom).label("lat"),
            func.ST_X(location_geom).label("lng"),
        ).where(Photo.id == photo_id)
        result = await self._session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        return float(row.lng), float(row.lat)

    async def create_pending(
        self,
        *,
        owner_id: UUID,
        storage_key_original: str,
        mime_type: str,
        size_bytes: int,
        lng: float,
        lat: float,
        width: int | None = None,
        height: int | None = None,
        taken_at: datetime | None = None,
        exif: dict | None = None,
    ) -> Photo:
        photo = Photo(
            owner_id=owner_id,
            storage_key_original=storage_key_original,
            mime_type=mime_type,
            size_bytes=size_bytes,
            width=width,
            height=height,
            taken_at=taken_at,
            location=WKTElement(f"POINT({lng} {lat})", srid=4326),
            exif=exif,
            ai_status="pending",
            visibility="private",
        )
        return await self.add(photo)
