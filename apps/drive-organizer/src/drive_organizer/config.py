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
        default="primary",
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

    confidence_threshold: float = Field(
        default=0.80,
        validation_alias="CONFIDENCE_THRESHOLD",
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

    # Model input limits
    max_download_bytes: int = Field(
        default=20_000_000,
        gt=0,
        validation_alias="MAX_DOWNLOAD_BYTES",
        description="Bytes downloaded per file for inspection",
    )
    max_document_chars: int = Field(
        default=24_000,
        gt=0,
        validation_alias="MAX_DOCUMENT_CHARS",
        description="Characters of extracted document text sent to the model",
    )
    pdf_max_pages: int = Field(
        default=10,
        gt=0,
        validation_alias="PDF_MAX_PAGES",
        description="PDF pages whose text is extracted",
    )
    triage_max_files: int = Field(
        default=200,
        gt=0,
        validation_alias="TRIAGE_MAX_FILES",
        description="Files listed in a folder manifest for folder triage",
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
