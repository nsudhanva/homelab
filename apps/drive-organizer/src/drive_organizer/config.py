from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Account identity
    account_name: str = Field(
        default="personal",
        validation_alias="ACCOUNT_NAME",
    )
    telegram_topic_id: int | None = Field(
        default=None,
        validation_alias="TELEGRAM_TOPIC_ID",
    )

    # Google OAuth credentials (supports both DRIVE_* and GMAIL_* env vars)
    drive_client_id: str = Field(
        default="",
        validation_alias="DRIVE_CLIENT_ID",
    )
    gmail_client_id: str = Field(
        default="",
        validation_alias="GMAIL_CLIENT_ID",
    )
    drive_client_secret: str = Field(
        default="",
        validation_alias="DRIVE_CLIENT_SECRET",
    )
    gmail_client_secret: str = Field(
        default="",
        validation_alias="GMAIL_CLIENT_SECRET",
    )
    drive_refresh_token: str = Field(
        default="",
        validation_alias="DRIVE_REFRESH_TOKEN",
    )
    gmail_refresh_token: str = Field(
        default="",
        validation_alias="GMAIL_REFRESH_TOKEN",
    )

    # LLM Provider Routing Settings
    primary_llm_provider: Literal["local", "openrouter"] = Field(
        default="local",
        validation_alias="PRIMARY_LLM_PROVIDER",
    )
    fallback_llm_provider: Literal["local", "openrouter", "none"] = Field(
        default="openrouter",
        validation_alias="FALLBACK_LLM_PROVIDER",
    )
    llm_base_url: str = Field(
        default="http://llama-server.llama.svc.cluster.local:8080/v1",
        validation_alias="LLM_BASE_URL",
    )
    llm_model_name: str = Field(
        default="gemma-4-e2b-it",
        validation_alias="LLM_MODEL_NAME",
    )
    llm_timeout_seconds: float = Field(
        default=120.0,
        validation_alias="LLM_TIMEOUT_SECONDS",
    )
    confidence_threshold: float = Field(
        default=0.80,
        validation_alias="CONFIDENCE_THRESHOLD",
    )

    # OpenRouter Fallback Settings
    openrouter_api_key: str = Field(
        default="",
        validation_alias="OPENROUTER_API_KEY",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias="OPENROUTER_BASE_URL",
    )
    openrouter_model_name: str = Field(
        default="google/gemma-4-31b-it",
        validation_alias="OPENROUTER_MODEL_NAME",
    )

    # Telegram alerts
    telegram_bot_token: str = Field(
        default="",
        validation_alias="TELEGRAM_BOT_TOKEN",
    )
    telegram_chat_id: str = Field(
        default="7341944813",
        validation_alias="TELEGRAM_CHAT_ID",
    )

    # Organizer behavior
    pacing_seconds: float = Field(
        default=1.5,
        validation_alias="PACING_SECONDS",
    )
    app_property_key: str = Field(
        default="ai_processed",
        validation_alias="DRIVE_APP_PROPERTY_KEY",
    )

    @property
    def client_id(self) -> str:
        return self.drive_client_id or self.gmail_client_id

    @property
    def client_secret(self) -> str:
        return self.drive_client_secret or self.gmail_client_secret

    @property
    def refresh_token(self) -> str:
        return self.drive_refresh_token or self.gmail_refresh_token
