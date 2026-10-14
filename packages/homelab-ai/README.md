# homelab-ai

A shared Python library for the homelab microservices. It gives high-availability LLM routing, Pydantic AI `FallbackModel` resilience, and agent factories.

## Features

- Pydantic AI native fallback: The primary model is the local GPU SLM (`gemma-4-e2b-it`). If a connection error, a timeout, or an HTTP 429/5xx status occurs, the library sends the request to OpenRouter (`google/gemma-4-31b-it`).
- Provider change at runtime: Change the primary and fallback providers with one environment variable each (`PRIMARY_LLM_PROVIDER`, `FALLBACK_LLM_PROVIDER`).
- OOP architecture: A strategy pattern for model providers (`LocalOpenAIProviderBuilder`, `OpenRouterProviderBuilder`) and a composable `ModelRouter` factory.
- Diagnostic unpacking: The library unwraps `FallbackExceptionGroup` cleanly for structured logging and metrics.
