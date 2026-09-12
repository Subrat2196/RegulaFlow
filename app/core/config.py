from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration for RegulaFlow.

    Every value here can be overridden by an environment variable or .env file.
    Pydantic validates each value at startup — if something is wrong, the app
    refuses to start rather than failing silently later.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application identity
    # -------------------------------------------------------------------------
    app_name: str = "RegulaFlow"
    app_version: str = "0.1.0"
    environment: str = Field(
        default="development",
        pattern="^(development|production|testing)$",
    )
    debug: bool = False

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return the cached Settings instance.

    @lru_cache means this function only runs once — the first call reads the
    .env file and environment variables, validates everything, and stores the
    result. Every call after that returns the same object instantly.

    In tests, create Settings() directly instead of calling get_settings(),
    so the cache does not bleed between test cases.
    """
    return Settings()
