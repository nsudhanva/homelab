"""Domain exceptions for homelab-ai routing and inference."""


class HomelabAIError(Exception):
    """Base exception for all homelab-ai errors."""


class LLMConnectionError(HomelabAIError, RuntimeError):
    """Every model in the chain was unreachable, timed out, or rate limited."""


class LLMOutputError(HomelabAIError, RuntimeError):
    """A model answered, but no answer passed output validation."""


class LLMConfigurationError(HomelabAIError, ValueError):
    """The model chain or provider settings are invalid."""
