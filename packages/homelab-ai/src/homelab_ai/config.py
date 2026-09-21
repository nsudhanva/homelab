"""Strongly-typed configuration schema for LLM provider routing."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProviderType = Literal["local", "openrouter"]
FallbackProviderType = Literal["local", "openrouter", "none"]


class LLMClientConfig(BaseSettings):
    """Configuration options for model routing and resilience."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    primary_provider: LLMProviderType = Field(
        default="local",
        validation_alias="PRIMARY_LLM_PROVIDER",
        description="Active primary provider ('local' or 'openrouter')",
    )
    fallback_provider: FallbackProviderType = Field(
        default="openrouter",
        validation_alias="FALLBACK_LLM_PROVIDER",
        description="Active fallback provider ('openrouter', 'local', or 'none')",
    )
    llm_base_url: str = Field(
        default="http://llama-server.llama.svc.cluster.local:8080/v1",
        validation_alias="LLM_BASE_URL",
        description="Base URL for the local llama-server OpenAI-compatible endpoint",
    )
    llm_model_name: str = Field(
        default="gemma-4-e2b-it",
        validation_alias="LLM_MODEL_NAME",
        description="Model slug or name for the local endpoint",
    )
    llm_timeout_seconds: float = Field(
        default=120.0,
        validation_alias="LLM_TIMEOUT_SECONDS",
        description="Per-request timeout in seconds for LLM inference",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias="OPENROUTER_BASE_URL",
        description="Base URL for the OpenRouter inference gateway",
    )
    openrouter_model_name: str = Field(
        default="google/gemma-4-31b-it",
        validation_alias="OPENROUTER_MODEL_NAME",
        description="Model slug or name for OpenRouter inference",
    )
    openrouter_api_key: str = Field(
        default="",
        validation_alias="OPENROUTER_API_KEY",
        description="API key for OpenRouter inference (injected from Vault)",
    )
    openrouter_timeout_seconds: float = Field(
        default=60.0,
        validation_alias="OPENROUTER_TIMEOUT_SECONDS",
        description="Per-request timeout in seconds for OpenRouter inference",
    )
    app_name: str = Field(
        default="homelab-ai",
        description="Application title passed in OpenRouter HTTP headers (X-Title)",
    )
    app_url: str = Field(
        default="https://github.com/nsudhanva/homelab",
        description="Application URL passed in OpenRouter HTTP headers (HTTP-Referer)",
    )
