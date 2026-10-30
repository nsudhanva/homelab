from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gmail_client_id: str = Field(
        validation_alias="GMAIL_CLIENT_ID",
        description="Google OAuth2 Client ID",
    )
    gmail_client_secret: str = Field(
        validation_alias="GMAIL_CLIENT_SECRET",
        description="Google OAuth2 Client Secret",
    )
    gmail_refresh_token: str = Field(
        validation_alias="GMAIL_REFRESH_TOKEN",
        description="Google OAuth2 Refresh Token",
    )
    telegram_bot_token: str | None = Field(
        default=None,
        validation_alias="TELEGRAM_BOT_TOKEN",
        description="Telegram bot token for notification dispatches",
    )
    telegram_chat_id: int = Field(
        default=7341944813,
        validation_alias="TELEGRAM_CHAT_ID",
        description="Telegram chat ID for alert delivery",
    )
    confidence_threshold: float = Field(
        default=0.80,
        validation_alias="CONFIDENCE_THRESHOLD",
        description="Confidence threshold below which emails are marked for ai-review",
    )
    quarantine_label: str = Field(
        default="ai-review",
        validation_alias="QUARANTINE_LABEL",
        description="Gmail label used for low-confidence or unclassified emails",
    )
    processed_label: str = Field(
        default="ai-processed",
        validation_alias="PROCESSED_LABEL",
        description="Gmail label indicating the email was processed by the classifier",
    )
    max_body_chars: int = Field(
        default=12_000,
        gt=0,
        validation_alias="MAX_BODY_CHARS",
        description="Characters of cleaned email body sent to the model",
    )
    concurrency: int = Field(
        default=4,
        validation_alias="CONCURRENCY",
        description="Number of concurrent message classification workers",
    )
    archive_older_than_days: int = Field(
        default=90,
        validation_alias="ARCHIVE_OLDER_THAN_DAYS",
        description="Archive classified emails older than this many days from INBOX",
    )
    auto_archive_enabled: bool = Field(
        default=True,
        validation_alias="AUTO_ARCHIVE_ENABLED",
        description="Whether to run the archive sweep for older classified emails",
    )
    account_name: str = Field(
        default="primary",
        validation_alias="ACCOUNT_NAME",
        description="Account identifier for this Google workload (e.g. primary, secondary)",
    )
    telegram_topic_id: int | None = Field(
        default=None,
        validation_alias="TELEGRAM_TOPIC_ID",
        description="Optional Telegram forum thread/topic ID for notification delivery",
    )
    allow_label_creation: bool = Field(
        default=True,
        validation_alias="ALLOW_LABEL_CREATION",
        description="Whether to autonomously discover and provision canonical labels",
    )
