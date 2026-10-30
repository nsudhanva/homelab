"""Provider registry that turns a ``ModelSpec`` into a Pydantic AI model."""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider

from .exceptions import LLMConfigurationError
from .settings import AISettings, ModelSpec

logger = logging.getLogger(__name__)

APP_URL = "https://github.com/nsudhanva/homelab"


@dataclass(frozen=True)
class ProviderContext:
    """Everything a provider builder needs to construct a model."""

    spec: ModelSpec
    settings: AISettings
    app_name: str
    timeout: float
    max_retries: int


@dataclass(frozen=True)
class Provider:
    """How to build models for one provider, and whether it is usable."""

    build: Callable[[ProviderContext], Model]
    is_configured: Callable[[AISettings], bool] = lambda _: True
    timeout_seconds: float = 60.0
    max_retries: int = 2


def _local(ctx: ProviderContext) -> Model:
    client = AsyncOpenAI(
        base_url=ctx.settings.local_base_url.rstrip("/"),
        api_key="local",
        timeout=ctx.timeout,
        max_retries=ctx.max_retries,
    )
    return OpenAIChatModel(ctx.spec.name, provider=OpenAIProvider(openai_client=client))


def _openrouter(ctx: ProviderContext) -> Model:
    key = ctx.settings.openrouter_api_key
    client = AsyncOpenAI(
        base_url=ctx.settings.openrouter_base_url.rstrip("/"),
        api_key=key.get_secret_value() if key else None,
        timeout=ctx.timeout,
        max_retries=ctx.max_retries,
        default_headers={"HTTP-Referer": APP_URL, "X-Title": ctx.app_name},
    )
    return OpenRouterModel(ctx.spec.name, provider=OpenRouterProvider(openai_client=client))


def _anthropic(ctx: ProviderContext) -> Model:
    key = ctx.settings.anthropic_api_key
    workspace = ctx.settings.anthropic_workspace_id
    client = AsyncAnthropic(
        api_key=key.get_secret_value() if key else None,
        base_url=ctx.settings.anthropic_base_url,
        timeout=ctx.timeout,
        max_retries=ctx.max_retries,
        default_headers={"anthropic-workspace-id": workspace} if workspace else None,
    )
    return AnthropicModel(
        ctx.spec.name,
        provider=AnthropicProvider(anthropic_client=client),
        settings=AnthropicModelSettings(
            anthropic_cache_instructions=True, anthropic_cache_tool_definitions=True
        ),
    )


def _openai(ctx: ProviderContext) -> Model:
    key = ctx.settings.openai_api_key
    client = AsyncOpenAI(
        base_url=ctx.settings.openai_base_url,
        api_key=key.get_secret_value() if key else None,
        timeout=ctx.timeout,
        max_retries=ctx.max_retries,
    )
    return OpenAIChatModel(ctx.spec.name, provider=OpenAIProvider(openai_client=client))


PROVIDERS: dict[str, Provider] = {
    "local": Provider(build=_local, timeout_seconds=120.0, max_retries=0),
    "openrouter": Provider(build=_openrouter, is_configured=lambda s: bool(s.openrouter_api_key)),
    "anthropic": Provider(build=_anthropic, is_configured=lambda s: bool(s.anthropic_api_key)),
    "openai": Provider(build=_openai, is_configured=lambda s: bool(s.openai_api_key)),
}


def register_provider(name: str, provider: Provider) -> None:
    """Add or replace a provider so ``<name>:<model>`` specs resolve to it."""
    PROVIDERS[name.lower()] = provider


def get_provider(spec: ModelSpec) -> Provider:
    try:
        return PROVIDERS[spec.provider]
    except KeyError:
        known = ", ".join(sorted(PROVIDERS))
        raise LLMConfigurationError(
            f"Unknown provider '{spec.provider}' in '{spec}'. Known providers: {known}"
        ) from None


def build_model(spec: ModelSpec, settings: AISettings, app_name: str = "homelab-ai") -> Model:
    """Build one model without fallback. Raises if its provider has no credentials."""
    provider = get_provider(spec)
    if not provider.is_configured(settings):
        raise LLMConfigurationError(f"Provider '{spec.provider}' has no credentials for '{spec}'")
    ctx = ProviderContext(
        spec=spec,
        settings=settings,
        app_name=app_name,
        timeout=settings.timeout_seconds or provider.timeout_seconds,
        max_retries=(
            settings.max_retries if settings.max_retries is not None else provider.max_retries
        ),
    )
    return provider.build(ctx)


def available_specs(settings: AISettings) -> list[ModelSpec]:
    """Models from the configured chain whose provider is known and has credentials."""
    usable = []
    for spec in settings.chain:
        if get_provider(spec).is_configured(settings):
            usable.append(spec)
        else:
            logger.info(f"Skipping {spec}: provider '{spec.provider}' has no credentials")
    return usable


def build_routed_model(settings: AISettings, app_name: str = "homelab-ai") -> Model:
    """Build the primary model wrapped in a fallback chain of every usable model."""
    specs = available_specs(settings)
    if not specs:
        chain = ", ".join(map(str, settings.chain))
        raise LLMConfigurationError(f"No usable models in chain [{chain}]; check credentials")
    return chain_models([build_model(spec, settings, app_name) for spec in specs])


def chain_models(models: list[Model]) -> Model:
    """Return the single model, or a FallbackModel that tries each in order."""
    if len(models) == 1:
        return models[0]
    return FallbackModel(*models, fallback_on=(ModelAPIError, UnexpectedModelBehavior))
