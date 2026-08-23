from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "Local Events API"
    api_prefix: str = "/api"
    jambase_base_url: str = Field(
        default="https://api.data.jambase.com/v3",
        alias="JAMBASE_BASE_URL",
    )
    jambase_api_key: str = Field(default="", alias="JAMBASE_API_KEY")
    jambase_timeout_seconds: float = Field(default=10.0, alias="JAMBASE_TIMEOUT_SECONDS")
    jambase_user_agent: str = Field(
        default="LocalEventsApp/1.0",
        alias="JAMBASE_USER_AGENT",
    )
    default_results_per_page: int = Field(default=12, alias="DEFAULT_RESULTS_PER_PAGE")
    max_results_per_page: int = Field(default=24, alias="MAX_RESULTS_PER_PAGE")
    event_window_days: int = Field(default=30, alias="EVENT_WINDOW_DAYS")
    backend_cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="BACKEND_CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        enable_decoding=False,
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
