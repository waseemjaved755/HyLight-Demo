from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_engine():
    import ssl

    settings = get_settings()
    connect_args: dict = {"statement_cache_size": 0}  # required for Supabase transaction pooler

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ctx

    return create_async_engine(
        settings.async_database_url,
        echo=settings.app_debug,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


engine = _build_engine()
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
