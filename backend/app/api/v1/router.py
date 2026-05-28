from fastapi import APIRouter

from app.api.v1 import comments, health, photos, users

api_router = APIRouter(prefix="/v1")
api_router.include_router(health.router)
api_router.include_router(users.router)
api_router.include_router(photos.router)
api_router.include_router(comments.router)
