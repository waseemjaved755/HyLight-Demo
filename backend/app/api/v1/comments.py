from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.comment import CommentCreateRequest, CommentResponse
from app.services.comment_service import CommentService

router = APIRouter(prefix="/photos/{photo_id}/comments", tags=["comments"])


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    photo_id: UUID,
    payload: CommentCreateRequest,
    user: CurrentUser,
    session: DbSession,
) -> CommentResponse:
    service = CommentService(session)
    try:
        return await service.create(photo_id=photo_id, author=user, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("", response_model=list[CommentResponse])
async def list_comments(
    photo_id: UUID,
    session: DbSession,
    response: Response,
) -> list[CommentResponse]:
    service = CommentService(session)
    comments, cache_source = await service.list_for_photo(photo_id)
    response.headers["X-Comments-Cache"] = cache_source
    return comments
