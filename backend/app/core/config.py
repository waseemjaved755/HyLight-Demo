from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    cors_origins: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS",
    )
    # Dev/ngrok only — allow any origin (*). Never enable in production.
    cors_allow_all: bool = Field(default=False, alias="CORS_ALLOW_ALL")

    # Option A (recommended): separate fields — matches Supabase Connect → Python → Transaction pooler
    database_host: str = Field(
        default="aws-1-eu-central-1.pooler.supabase.com",
        alias="DATABASE_HOST",
    )
    database_port: int = Field(default=6543, alias="DATABASE_PORT")
    database_name: str = Field(default="postgres", alias="DATABASE_NAME")
    database_user: str = Field(
        default="postgres.zcihmzsfogsfdbmksfss",
        alias="DATABASE_USER",
    )
    database_password: str | None = Field(default=None, alias="DATABASE_PASSWORD")

    # Option B: paste full URI from Supabase (use only if DATABASE_PASSWORD is not set)
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    redis_enabled: bool = Field(default=True, alias="REDIS_ENABLED")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_jwt_secret: str = Field(alias="SUPABASE_JWT_SECRET")
    # Legacy JWT `service_role` or new `sb_secret_...` — optional if client sends signed image_url
    supabase_service_role_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SECRET_KEY"),
    )
    storage_bucket: str = Field(default="Photos", alias="STORAGE_BUCKET")

    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    # Free tier: gemini-2.0-flash often hits 429; gemini-2.5-flash works reliably
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    @model_validator(mode="after")
    def require_database_credentials(self) -> "Settings":
        if not self.database_password and not self.database_url:
            raise ValueError(
                "Set DATABASE_PASSWORD (recommended) or DATABASE_URL in backend/.env"
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def async_database_url(self) -> str:
        """Async SQLAlchemy URL for FastAPI (Supabase docs use psycopg2 sync URL)."""
        if self.database_password:
            encoded = quote_plus(self.database_password)
            return (
                f"postgresql+asyncpg://{self.database_user}:{encoded}"
                f"@{self.database_host}:{self.database_port}/{self.database_name}"
            )

        assert self.database_url is not None
        url = self.database_url.strip()
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Sync URL for psycopg2 — same format as Supabase dashboard snippet."""
        if self.database_password:
            encoded = quote_plus(self.database_password)
            return (
                f"postgresql://{self.database_user}:{encoded}"
                f"@{self.database_host}:{self.database_port}/{self.database_name}"
            )

        assert self.database_url is not None
        url = self.database_url.strip()
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
