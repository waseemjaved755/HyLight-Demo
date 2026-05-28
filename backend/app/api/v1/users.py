from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.user import UserResponse

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
