from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path



BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "AI Product Discovery Engine API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    database_url: str
    youtube_api_key: str
    openrouter_api_key: str
    openrouter_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE ,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Using lru_cache ensures the .env file is read only once
    during the application's lifetime.
    """
    return Settings()