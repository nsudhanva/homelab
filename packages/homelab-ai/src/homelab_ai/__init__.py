"""homelab-ai: High-availability LLM routing and resilience for homelab services."""

from .config import FallbackProviderType, LLMClientConfig, LLMProviderType
from .exceptions import HomelabAIError, LLMConfigurationError, LLMConnectionError
from .providers import (
    BaseProviderBuilder,
    CustomModelProviderBuilder,
    LocalOpenAIProviderBuilder,
    OpenRouterProviderBuilder,
    register_provider,
)
from .router import ModelRouter

__all__ = [
    "BaseProviderBuilder",
    "CustomModelProviderBuilder",
    "FallbackProviderType",
    "HomelabAIError",
    "LLMClientConfig",
    "LLMConfigurationError",
    "LLMConnectionError",
    "LLMProviderType",
    "LocalOpenAIProviderBuilder",
    "ModelRouter",
    "OpenRouterProviderBuilder",
    "register_provider",
]
