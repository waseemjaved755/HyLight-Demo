from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    configure_logging(debug=settings.app_debug)
    logger.info("api_starting", env=settings.app_env)
    yield
    logger.info("api_stopping")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Photo Map API",
        version="0.1.0",
        lifespan=lifespan,
    )
    if settings.cors_allow_all:
        logger.warning("cors_allow_all_enabled", detail="All origins allowed — dev/ngrok only")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(api_router)
    return app


app = create_app()
