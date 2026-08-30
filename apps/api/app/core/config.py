from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "AI Product Discovery Engine API"
    app_version: str = "0.1.0"

    environment: str = "development"
    debug: bool = False

    database_url: str

    youtube_api_key: str | None = None

    openrouter_api_key: str | None = None
    openrouter_model: str = "minimax/minimax-m3:free"
    openrouter_embedding_model: str | None = None

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Environment variables take precedence over values stored
    in the local .env file.
    """
    return Settings()