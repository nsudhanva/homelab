"""Configuration and environment settings for Actual Classifier."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from homelab_ai import FallbackProviderType, LLMClientConfig, LLMProviderType


class Settings(BaseSettings):
    """Runtime application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Actual Budget Connection
    actual_server_url: str = Field(
        default="http://actual-budget.actual-budget.svc.cluster.local:5006",
        validation_alias="ACTUAL_SERVER_URL",
    )
    actual_password: str = Field(
        default="",
        validation_alias="ACTUAL_PASSWORD",
    )
    actual_budget_name: str = Field(
        default="My Finances",
        validation_alias="ACTUAL_BUDGET_NAME",
    )

    # LLM Router Settings
    primary_llm_provider: LLMProviderType = Field(
        default="local",
        validation_alias="PRIMARY_LLM_PROVIDER",
    )
    fallback_llm_provider: FallbackProviderType = Field(
        default="openrouter",
        validation_alias="FALLBACK_LLM_PROVIDER",
    )
    llm_base_url: str = Field(
        default="http://llama-server.llama.svc.cluster.local:8080/v1",
        validation_alias="LLM_BASE_URL",
    )
    llm_model: str = Field(
        default="gemma-4-e2b-it",
        validation_alias="LLM_MODEL",
    )
    llm_timeout_seconds: float = Field(
        default=60.0,
        validation_alias="LLM_TIMEOUT_SECONDS",
    )
    openrouter_api_key: str = Field(
        default="",
        validation_alias="OPENROUTER_API_KEY",
    )
    openrouter_model_name: str = Field(
        default="google/gemma-4-31b-it",
        validation_alias="OPENROUTER_MODEL_NAME",
    )

    # Classification Behavior
    confidence_threshold: float = Field(
        default=0.6,
        validation_alias="CONFIDENCE_THRESHOLD",
        description=(
            "Minimum confidence score required to auto-classify; below this #Unknown is retained"
        ),
    )
    batch_size: int = Field(
        default=25,
        validation_alias="BATCH_SIZE",
        description="Maximum transactions to classify in one execution run",
    )

    def to_llm_client_config(self) -> LLMClientConfig:
        """Convert settings to homelab-ai standard LLMClientConfig."""
        return LLMClientConfig(
            primary_provider=self.primary_llm_provider,
            fallback_provider=self.fallback_llm_provider,
            llm_base_url=self.llm_base_url,
            llm_model_name=self.llm_model,
            llm_timeout_seconds=self.llm_timeout_seconds,
            openrouter_api_key=self.openrouter_api_key,
            openrouter_model_name=self.openrouter_model_name,
            app_name="homelab-actual-classifier",
        )
