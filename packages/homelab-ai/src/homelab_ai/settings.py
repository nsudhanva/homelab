"""Environment-driven configuration shared by every homelab AI workload."""

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from .exceptions import LLMConfigurationError

DEFAULT_MODEL = "anthropic:claude-haiku-5-5"
DEFAULT_FALLBACK_MODELS = ("openrouter:google/gemma-4-31b-it", "local:gemma-4-e2b-it")
DEFAULT_LOCAL_BASE_URL = "http://llama-server.llama.svc.cluster.local:8080/v1"


@dataclass(frozen=True)
class ModelSpec:
    """A provider-qualified model reference such as ``anthropic:claude-haiku-5-5``."""

    provider: str
    name: str

    @classmethod
    def parse(cls, value: str) -> "ModelSpec":
        provider, sep, name = value.strip().partition(":")
        if not sep or not provider or not name:
            raise LLMConfigurationError(
                f"Invalid model spec '{value}'. Use '<provider>:<model>', "
                "for example 'local:gemma-4-e2b-it' or 'anthropic:claude-haiku-5-5'."
            )
        return cls(provider=provider.lower(), name=name)

    def __str__(self) -> str:
        return f"{self.provider}:{self.name}"


def _parse_specs(value: Any) -> list[ModelSpec]:
    if isinstance(value, str):
        value = [] if value.strip().lower() in {"", "none"} else value.split(",")
    return [v if isinstance(v, ModelSpec) else ModelSpec.parse(v) for v in value if str(v).strip()]


class AISettings(BaseSettings):
    """Model chain, tuning, and provider credentials, read from the environment.

    ``AI_MODEL`` is the primary model and ``AI_FALLBACK_MODELS`` is a comma-separated
    chain tried in order when the previous model fails. Models whose provider has no
    credentials are skipped, so the same chain works on a laptop and in the cluster.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    model: Annotated[ModelSpec, NoDecode] = Field(
        default=ModelSpec.parse(DEFAULT_MODEL), validation_alias="AI_MODEL"
    )
    fallback_models: Annotated[list[ModelSpec], NoDecode] = Field(
        default_factory=lambda: _parse_specs(DEFAULT_FALLBACK_MODELS),
        validation_alias="AI_FALLBACK_MODELS",
    )
    timeout_seconds: float | None = Field(default=None, validation_alias="AI_TIMEOUT_SECONDS")
    max_retries: int | None = Field(default=None, validation_alias="AI_MAX_RETRIES")
    attempts: int = Field(default=2, ge=1, validation_alias="AI_ATTEMPTS")
    retry_backoff_seconds: float = Field(
        default=5.0, ge=0.0, validation_alias="AI_RETRY_BACKOFF_SECONDS"
    )
    temperature: float | None = Field(default=None, validation_alias="AI_TEMPERATURE")
    max_tokens: int | None = Field(default=None, validation_alias="AI_MAX_TOKENS")
    effort: Literal["low", "medium", "high", "xhigh", "max"] | None = Field(
        default=None, validation_alias="AI_EFFORT"
    )

    local_base_url: str = Field(
        default=DEFAULT_LOCAL_BASE_URL, validation_alias="LOCAL_LLM_BASE_URL"
    )
    openrouter_api_key: SecretStr | None = Field(
        default=None, validation_alias="OPENROUTER_API_KEY"
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", validation_alias="OPENROUTER_BASE_URL"
    )
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    anthropic_workspace_id: str | None = Field(
        default=None, validation_alias="ANTHROPIC_WORKSPACE_ID"
    )
    anthropic_base_url: str | None = Field(default=None, validation_alias="ANTHROPIC_BASE_URL")
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, validation_alias="OPENAI_BASE_URL")

    @field_validator("model", mode="before")
    @classmethod
    def _parse_model(cls, value: Any) -> ModelSpec:
        return value if isinstance(value, ModelSpec) else ModelSpec.parse(value)

    @field_validator("fallback_models", mode="before")
    @classmethod
    def _parse_fallbacks(cls, value: Any) -> list[ModelSpec]:
        return _parse_specs(value)

    @property
    def chain(self) -> list[ModelSpec]:
        """Primary model followed by fallbacks, without duplicates."""
        return list(dict.fromkeys([self.model, *self.fallback_models]))
