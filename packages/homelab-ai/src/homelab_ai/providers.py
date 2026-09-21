"""Provider builders implementing the Factory Method and Strategy patterns."""

from abc import ABC, abstractmethod

from openai import AsyncOpenAI
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider

from .config import LLMClientConfig


class BaseProviderBuilder(ABC):
    """Abstract base builder for LLM providers."""

    @abstractmethod
    def build(self, config: LLMClientConfig) -> Model:
        """Construct and return a configured Pydantic AI Model instance."""


class LocalOpenAIProviderBuilder(BaseProviderBuilder):
    """Builder for local llama-server (OpenAI-compatible) endpoint."""

    def build(self, config: LLMClientConfig) -> Model:
        client = AsyncOpenAI(
            base_url=config.llm_base_url.rstrip("/"),
            api_key="not-needed",
            timeout=config.llm_timeout_seconds,
        )
        provider = OpenAIProvider(openai_client=client)
        return OpenAIChatModel(
            model_name=config.llm_model_name,
            provider=provider,
        )


class OpenRouterProviderBuilder(BaseProviderBuilder):
    """Builder for OpenRouter cloud inference gateway."""

    def build(self, config: LLMClientConfig) -> Model:
        headers: dict[str, str] = {}
        if config.app_url:
            headers["HTTP-Referer"] = config.app_url
        if config.app_name:
            headers["X-Title"] = config.app_name

        client = AsyncOpenAI(
            base_url=config.openrouter_base_url.rstrip("/"),
            api_key=config.openrouter_api_key,
            timeout=config.openrouter_timeout_seconds,
            default_headers=headers if headers else None,
        )
        provider = OpenRouterProvider(openai_client=client)
        return OpenRouterModel(
            model_name=config.openrouter_model_name,
            provider=provider,
        )


class CustomModelProviderBuilder(BaseProviderBuilder):
    """Builder that returns an externally supplied model (e.g. for testing)."""

    def __init__(self, model: Model) -> None:
        self._model = model

    def build(self, config: LLMClientConfig) -> Model:
        return self._model


PROVIDER_REGISTRY: dict[str, type[BaseProviderBuilder]] = {
    "local": LocalOpenAIProviderBuilder,
    "openrouter": OpenRouterProviderBuilder,
}


def register_provider(name: str, builder_cls: type[BaseProviderBuilder]) -> None:
    """Register an extension provider builder for future model engines."""
    PROVIDER_REGISTRY[name.lower()] = builder_cls
