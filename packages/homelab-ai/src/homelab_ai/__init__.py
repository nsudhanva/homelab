"""homelab-ai: one model chain, one task API, every provider, for all homelab AI jobs."""

from .exceptions import HomelabAIError, LLMConfigurationError, LLMConnectionError, LLMOutputError
from .providers import Provider, ProviderContext, build_model, build_routed_model, register_provider
from .settings import AISettings, ModelSpec
from .task import AITask, is_transient

__all__ = [
    "AISettings",
    "AITask",
    "HomelabAIError",
    "LLMConfigurationError",
    "LLMConnectionError",
    "LLMOutputError",
    "ModelSpec",
    "Provider",
    "ProviderContext",
    "build_model",
    "build_routed_model",
    "is_transient",
    "register_provider",
]
