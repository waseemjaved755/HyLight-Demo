from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.photo import (
    MapPhotosResponse,
    PhotoDescribeRequest,
    PhotoResponse,
    PhotoUploadInitRequest,
    PhotoUploadInitResponse,
)
from app.services.photo_service import PhotoService
from app.services.photo_tasks import run_photo_description_background

router = APIRouter(prefix="/photos", tags=["photos"])


@router.post("/upload-url", response_model=PhotoUploadInitResponse, status_code=status.HTTP_201_CREATED)
async def init_upload(
    payload: PhotoUploadInitRequest,
    user: CurrentUser,
    session: DbSession,
) -> PhotoUploadInitResponse:
    service = PhotoService(session)
    return await service.init_upload(owner=user, payload=payload)


@router.get("/map/viewport", response_model=MapPhotosResponse)
async def map_viewport(
    session: DbSession,
    user: CurrentUser,
    min_lng: float = Query(..., ge=-180, le=180),
    min_lat: float = Query(..., ge=-90, le=90),
    max_lng: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
) -> MapPhotosResponse:
    service = PhotoService(session)
    return await service.map_photos(
        min_lng=min_lng,
        min_lat=min_lat,
        max_lng=max_lng,
        max_lat=max_lat,
        viewer_id=user.id,
    )


@router.post("/{photo_id}/finalize", response_model=PhotoResponse)
async def finalize_upload(
    photo_id: UUID,
    user: CurrentUser,
    session: DbSession,
    background_tasks: BackgroundTasks,
) -> PhotoResponse:
    service = PhotoService(session)
    try:
        response = await service.finalize(photo_id, user.id)
        background_tasks.add_task(run_photo_description_background, photo_id, user.id)
        return response
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(
    photo_id: UUID,
    session: DbSession,
    user: CurrentUser,
    response: Response,
) -> PhotoResponse:
    service = PhotoService(session)
    photo, cache_source = await service.get_photo(photo_id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    response.headers["X-Photo-Cache"] = cache_source
    return photo


@router.post("/{photo_id}/describe", response_model=PhotoResponse)
async def describe_photo(
    photo_id: UUID,
    user: CurrentUser,
    session: DbSession,
    payload: PhotoDescribeRequest = PhotoDescribeRequest(),
) -> PhotoResponse:
    service = PhotoService(session)
    image_url = payload.image_url
    try:
        return await service.generate_description(
            photo_id,
            user.id,
            image_url=image_url,
            retry=payload.retry,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
