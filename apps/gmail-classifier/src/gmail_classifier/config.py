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
    llm_base_url: str = Field(
        default="http://llama-server.llama.svc.cluster.local:8080/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "llm_base_url"),
        description="OpenAI-compatible LLM endpoint base URL",
    )
    llm_model: str = Field(
        default="gemma-4-e2b-it",
        validation_alias=AliasChoices("LLM_MODEL", "llm_model"),
        description="Target model identifier",
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
    concurrency: int = Field(
        default=2,
        validation_alias=AliasChoices("CONCURRENCY", "concurrency"),
        description="Number of concurrent message classification workers",
    )
