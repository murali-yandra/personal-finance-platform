from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    enable_ai: bool = False
    enable_telegram: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
