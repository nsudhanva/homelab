"""Domain exceptions for homelab-ai routing and inference."""


class HomelabAIError(Exception):
    """Base exception for all homelab-ai errors."""


class LLMConnectionError(HomelabAIError, RuntimeError):
    """Raised when the LLM server or fallback is unreachable or timed out."""


class LLMConfigurationError(HomelabAIError, ValueError):
    """Raised when LLM configuration or provider settings are invalid."""
