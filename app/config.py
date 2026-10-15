from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "carecloud-voice-agent"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    database_url: str = Field(default="sqlite:///./patients.db")
    google_api_key: str = Field(default="")
    vapi_api_key: str = Field(default="")
    vapi_phone_number: str = Field(default="")
    secret_key: str = Field(default="change-me")


settings = Settings()
