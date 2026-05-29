from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.api.v1.http_errors import from_value_error
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
        raise from_value_error(exc) from exc


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


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    photo_id: UUID,
    comment_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> None:
    service = CommentService(session)
    try:
        await service.delete(photo_id=photo_id, comment_id=comment_id, user=user)
    except ValueError as exc:
        raise from_value_error(exc) from exc
