from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Local Events API"
    api_prefix: str = "/api"
    jambase_api_key: str = Field(default="", alias="JAMBASE_API_KEY")
    backend_cors_origins: list[str] = Field(
        default=["http://localhost:5173"],
        alias="BACKEND_CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
