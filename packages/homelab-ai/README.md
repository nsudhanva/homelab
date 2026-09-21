# homelab-ai

Shared Python library for high-availability LLM routing, Pydantic AI `FallbackModel` resilience, and agent factories across homelab microservices.

## Features

- **Pydantic AI Native Fallback**: Routes requests from local GPU SLM (`gemma-4-e2b-it`) to OpenRouter (`google/gemma-4-31b-it`) upon connection errors, timeouts, or HTTP 429/5xx status codes.
- **Dynamic Provider Flipping**: Switch primary and fallback providers with a single environment variable (`PRIMARY_LLM_PROVIDER`, `FALLBACK_LLM_PROVIDER`).
- **OOP Architecture**: Strategy pattern for model providers (`LocalOpenAIProviderBuilder`, `OpenRouterProviderBuilder`) and composable `ModelRouter` factory.
- **Diagnostic Unpacking**: Clean unwrapping of `FallbackExceptionGroup` for structured logging and metrics.
