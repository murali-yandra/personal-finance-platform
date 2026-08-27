from functools import lru_cache
from typing import Annotated

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Personal Finance Tracking Platform"
    app_env: str = "development"
    app_version: str = "0.1.0"
    app_debug: bool = False
    log_level: str = "INFO"

    database_url: str
    database_echo: bool = False

    jwt_secret: SecretStr
    ingest_api_key: SecretStr
    ingest_user_email: str = ""

    enable_ai: bool = False
    enable_telegram: bool = False

    cors_origins: Annotated[list[str], NoDecode] = []

    @field_validator("database_url", mode="after")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Force the psycopg driver on managed-Postgres connection strings.

        Hosting providers hand out ``postgres://`` or ``postgresql://`` URLs, which
        SQLAlchemy resolves to psycopg2. This project ships psycopg 3, so the driver
        has to be named explicitly.
        """
        for prefix in ("postgresql+", "postgres+"):
            if value.startswith(prefix):
                return value
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        """Accept a comma-separated CORS origin list from the environment."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
