from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gmail_client_id: str = Field(
        validation_alias=AliasChoices(
            "GMAIL_CLIENT_ID", "gmail_client_id", "client_id", "CLIENT_ID"
        ),
        description="Google OAuth2 Client ID",
    )
    gmail_client_secret: str = Field(
        validation_alias=AliasChoices(
            "GMAIL_CLIENT_SECRET", "gmail_client_secret", "client_secret", "CLIENT_SECRET"
        ),
        description="Google OAuth2 Client Secret",
    )
    gmail_refresh_token: str = Field(
        validation_alias=AliasChoices(
            "GMAIL_REFRESH_TOKEN", "gmail_refresh_token", "refresh_token", "REFRESH_TOKEN"
        ),
        description="Google OAuth2 Refresh Token",
    )
    telegram_bot_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "TELEGRAM_BOT_TOKEN", "telegram_bot_token", "bot_token", "BOT_TOKEN"
        ),
        description="Telegram bot token for notification dispatches",
    )
    telegram_chat_id: int = Field(
        default=7341944813,
        validation_alias=AliasChoices("TELEGRAM_CHAT_ID", "telegram_chat_id", "chat_id", "CHAT_ID"),
        description="Telegram chat ID for alert delivery",
    )
    confidence_threshold: float = Field(
        default=0.80,
        validation_alias=AliasChoices("CONFIDENCE_THRESHOLD", "confidence_threshold"),
        description="Confidence threshold below which emails are marked for ai-review",
    )
    quarantine_label: str = Field(
        default="ai-review",
        validation_alias=AliasChoices("QUARANTINE_LABEL", "quarantine_label"),
        description="Gmail label used for low-confidence or unclassified emails",
    )
    processed_label: str = Field(
        default="ai-processed",
        validation_alias=AliasChoices("PROCESSED_LABEL", "processed_label"),
        description="Gmail label indicating the email was processed by the classifier",
    )
    max_body_chars: int = Field(
        default=12_000,
        gt=0,
        validation_alias=AliasChoices("MAX_BODY_CHARS", "max_body_chars"),
        description="Characters of cleaned email body sent to the model",
    )
    concurrency: int = Field(
        default=4,
        validation_alias=AliasChoices("CONCURRENCY", "concurrency"),
        description="Number of concurrent message classification workers",
    )
    archive_older_than_days: int = Field(
        default=90,
        validation_alias=AliasChoices("ARCHIVE_OLDER_THAN_DAYS", "archive_older_than_days"),
        description="Archive classified emails older than this many days from INBOX",
    )
    auto_archive_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("AUTO_ARCHIVE_ENABLED", "auto_archive_enabled"),
        description="Whether to run the archive sweep for older classified emails",
    )
    account_name: str = Field(
        default="primary",
        validation_alias=AliasChoices("ACCOUNT_NAME", "account_name"),
        description="Account identifier for this Google workload (e.g. primary, secondary)",
    )
    telegram_topic_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("TELEGRAM_TOPIC_ID", "telegram_topic_id"),
        description="Optional Telegram forum thread/topic ID for notification delivery",
    )
    allow_label_creation: bool = Field(
        default=True,
        validation_alias=AliasChoices("ALLOW_LABEL_CREATION", "allow_label_creation"),
        description="Whether to autonomously discover and provision canonical labels",
    )
