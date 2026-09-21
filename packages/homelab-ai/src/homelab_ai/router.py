"""High-availability model router implementing Pydantic AI FallbackModel routing."""

import logging
from typing import Any, TypeVar

from pydantic_ai import Agent
from pydantic_ai.exceptions import FallbackExceptionGroup, ModelAPIError
from pydantic_ai.models import Model
from pydantic_ai.models.fallback import FallbackModel

from .config import LLMClientConfig
from .exceptions import LLMConfigurationError
from .providers import (
    PROVIDER_REGISTRY,
    BaseProviderBuilder,
    LocalOpenAIProviderBuilder,
)

logger = logging.getLogger(__name__)

OutputT = TypeVar("OutputT")
DepsT = TypeVar("DepsT")


class ModelRouter:
    """Orchestrates model selection, FallbackModel wiring, and Agent creation."""

    def __init__(
        self,
        config: LLMClientConfig | None = None,
        custom_primary_builder: BaseProviderBuilder | None = None,
        custom_fallback_builder: BaseProviderBuilder | None = None,
    ) -> None:
        self.config = config or LLMClientConfig()
        self._custom_primary_builder = custom_primary_builder
        self._custom_fallback_builder = custom_fallback_builder

    def build_primary_model(self, override: Model | None = None) -> Model:
        """Construct the configured primary model."""
        if override is not None:
            return override
        if self._custom_primary_builder is not None:
            return self._custom_primary_builder.build(self.config)

        provider_name = self.config.primary_provider.lower()
        builder_cls = PROVIDER_REGISTRY.get(provider_name)
        if not builder_cls:
            raise LLMConfigurationError(f"Unknown primary LLM provider: {provider_name}")

        if provider_name == "openrouter" and not self.config.openrouter_api_key:
            logger.warning(
                "Primary provider is openrouter but OPENROUTER_API_KEY is not set! "
                "Falling back to local."
            )
            return LocalOpenAIProviderBuilder().build(self.config)

        return builder_cls().build(self.config)

    def build_fallback_model(self, override: Model | None = None) -> Model | None:
        """Construct the configured fallback model, or None if disabled."""
        if override is not None:
            return override
        if self._custom_fallback_builder is not None:
            return self._custom_fallback_builder.build(self.config)

        fb_provider = self.config.fallback_provider.lower()
        if fb_provider == "none":
            return None

        # Do not fall back to the same provider as primary
        if fb_provider == self.config.primary_provider.lower():
            logger.warning(
                f"Fallback provider '{fb_provider}' is identical to primary; fallback disabled."
            )
            return None

        if fb_provider == "openrouter" and not self.config.openrouter_api_key:
            logger.info("OpenRouter fallback disabled because OPENROUTER_API_KEY is empty.")
            return None

        builder_cls = PROVIDER_REGISTRY.get(fb_provider)
        if not builder_cls:
            logger.warning(f"Unknown fallback LLM provider: '{fb_provider}'; fallback disabled.")
            return None

        return builder_cls().build(self.config)

    def build_routed_model(
        self,
        primary_override: Model | None = None,
        fallback_override: Model | None = None,
    ) -> Model:
        """Construct a high-availability FallbackModel or standalone model."""
        primary = self.build_primary_model(override=primary_override)
        fallback = self.build_fallback_model(override=fallback_override)

        if (
            self.config.primary_provider == "openrouter"
            and not self.config.openrouter_api_key
            and self.config.fallback_provider == "local"
            and fallback_override is None
        ):
            return primary

        if fallback is not None:
            logger.debug(
                f"Configuring FallbackModel (primary={self.config.primary_provider}, "
                f"fallback={self.config.fallback_provider})"
            )
            return FallbackModel(primary, fallback, fallback_on=(ModelAPIError,))

        return primary

    def create_agent(
        self,
        output_type: type[OutputT] | Any = None,
        system_prompt: str | None = None,
        deps_type: Any = type[None],
        retries: int = 2,
        primary_override: Model | None = None,
        fallback_override: Model | None = None,
    ) -> Agent[Any, Any]:
        """Factory method to construct a typed Pydantic AI Agent with model routing."""
        routed_model = self.build_routed_model(
            primary_override=primary_override,
            fallback_override=fallback_override,
        )

        agent_kwargs: dict[str, Any] = {
            "model": routed_model,
            "deps_type": deps_type,
            "retries": retries,
        }
        if output_type is not None:
            agent_kwargs["output_type"] = output_type
        if system_prompt is not None:
            agent_kwargs["system_prompt"] = system_prompt

        return Agent(**agent_kwargs)

    @staticmethod
    def unwrap_fallback_error(exc: Exception) -> list[Exception]:
        """Extract underlying candidate exceptions from FallbackExceptionGroup."""
        if isinstance(exc, FallbackExceptionGroup):
            return list(exc.exceptions)
        return [exc]
