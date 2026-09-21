from homelab_ai.config import FallbackProviderType, LLMClientConfig, LLMProviderType
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Provider Routing Settings
    primary_llm_provider: LLMProviderType = Field(
        default="local",
        validation_alias=AliasChoices("PRIMARY_LLM_PROVIDER", "primary_llm_provider"),
        description="Active primary LLM provider ('local' or 'openrouter')",
    )
    fallback_llm_provider: FallbackProviderType = Field(
        default="openrouter",
        validation_alias=AliasChoices("FALLBACK_LLM_PROVIDER", "fallback_llm_provider"),
        description="Active fallback LLM provider ('openrouter', 'local', or 'none')",
    )
    llm_timeout_seconds: float = Field(
        default=120.0,
        validation_alias=AliasChoices("LLM_TIMEOUT_SECONDS", "llm_timeout_seconds"),
        description="Timeout for LLM inference requests",
    )
    openrouter_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "openrouter_api_key"),
        description="OpenRouter API key injected from Vault",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices("OPENROUTER_BASE_URL", "openrouter_base_url"),
        description="Base URL for OpenRouter",
    )
    openrouter_model_name: str = Field(
        default="google/gemma-4-31b-it",
        validation_alias=AliasChoices("OPENROUTER_MODEL_NAME", "openrouter_model_name"),
        description="Model slug for OpenRouter inference",
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

    def to_llm_client_config(self) -> LLMClientConfig:
        return LLMClientConfig(
            primary_provider=self.primary_llm_provider,
            fallback_provider=self.fallback_llm_provider,
            llm_base_url=self.llm_base_url,
            llm_model_name=self.llm_model,
            llm_timeout_seconds=self.llm_timeout_seconds,
            openrouter_base_url=self.openrouter_base_url,
            openrouter_model_name=self.openrouter_model_name,
            openrouter_api_key=self.openrouter_api_key,
            app_name="homelab-gmail-classifier",
            app_url="https://github.com/nsudhanva/homelab",
        )
