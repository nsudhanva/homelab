---
title: How to Build and Extend AI Applications with Automatic Fallback
description: Problem-oriented guide on building or extending homelab microservices with shared homelab-ai routing and OpenRouter failover.
keywords:
  - add ai application
  - homelab-ai guide
  - pydantic-ai fallback
  - monorepo ai package
sidebar:
  order: 25
---

# How to Build and Extend AI Applications with Automatic Fallback

This guide walks through building a new AI microservice or extending an existing application with automatic local-to-cloud model fallback using `packages/homelab-ai`.

---

## Step 1: Declare the homelab-ai Dependency

In your application directory (`apps/{your-app}/pyproject.toml`), add `homelab-ai` to your dependencies and configure `[tool.uv.sources]`:

```toml
[project]
name = "my-new-app"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.9.0",
    "pydantic-ai>=2.43.0",
    "pydantic-settings>=2.5.0",
    "homelab-ai",
]

[tool.uv.sources]
homelab-ai = { path = "../../packages/homelab-ai", editable = true }
```

Lock dependencies using `uv`:

```bash
cd apps/{your-app}
uv lock
uv sync
```

---

## Step 2: Configure Settings and the ModelRouter

In your application's `config.py`, import the standard provider types from `homelab_ai`:

```python
from homelab_ai import FallbackProviderType, LLMClientConfig, LLMProviderType
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    primary_llm_provider: LLMProviderType = Field(
        default="local",
        validation_alias="PRIMARY_LLM_PROVIDER",
    )
    fallback_llm_provider: FallbackProviderType = Field(
        default="openrouter",
        validation_alias="FALLBACK_LLM_PROVIDER",
    )
    llm_base_url: str = Field(
        default="http://llama-server.llama.svc.cluster.local:8080/v1",
        validation_alias="LLM_BASE_URL",
    )
    llm_model: str = Field(
        default="gemma-4-e2b-it",
        validation_alias="LLM_MODEL",
    )
    llm_timeout_seconds: float = Field(
        default=120.0,
        validation_alias="LLM_TIMEOUT_SECONDS",
    )
    openrouter_api_key: str = Field(
        default="",
        validation_alias="OPENROUTER_API_KEY",
    )
    openrouter_model_name: str = Field(
        default="google/gemma-4-31b-it",
        validation_alias="OPENROUTER_MODEL_NAME",
    )

    def to_llm_client_config(self) -> LLMClientConfig:
        return LLMClientConfig(
            primary_provider=self.primary_llm_provider,
            fallback_provider=self.fallback_llm_provider,
            llm_base_url=self.llm_base_url,
            llm_model_name=self.llm_model,
            llm_timeout_seconds=self.llm_timeout_seconds,
            openrouter_api_key=self.openrouter_api_key,
            openrouter_model_name=self.openrouter_model_name,
            app_name="homelab-my-new-app",
        )
```

In your application service or worker, instantiate the router and create the agent:

```python
from homelab_ai import ModelRouter
from pydantic import BaseModel


class AnalysisOutput(BaseModel):
    summary: str
    action_required: bool


class MyService:
    def __init__(self, settings: Settings) -> None:
        self.router = ModelRouter(settings.to_llm_client_config())
        self.agent = self.router.create_agent(
            output_type=AnalysisOutput,
            system_prompt="Analyze the input and return structured recommendations.",
        )

    def run_sync(self, text: str) -> AnalysisOutput:
        result = self.agent.run_sync(text)
        return result.output
```

---

## Step 3: Write Hermetic Fallback Unit Tests

Verify that fallback works when the local LLM fails by injecting mock models via `CustomModelProviderBuilder`:

```python
from homelab_ai import LLMClientConfig, ModelRouter
from homelab_ai.providers import CustomModelProviderBuilder
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.models.test import TestModel


def test_service_failover_to_openrouter() -> None:
    class FailingLocalModel(TestModel):
        async def request(self, *args, **kwargs):
            raise ModelAPIError(
                model_name="gemma-4-e2b-it", message="Local LLM crashed"
            )

    fallback_model = TestModel(
        custom_output_args={"summary": "Rescued by cloud", "action_required": True}
    )

    router = ModelRouter(
        config=LLMClientConfig(
            primary_provider="local",
            fallback_provider="openrouter",
            openrouter_api_key="test-key",
        ),
        custom_primary_builder=CustomModelProviderBuilder(FailingLocalModel()),
        custom_fallback_builder=CustomModelProviderBuilder(fallback_model),
    )

    agent = router.create_agent(output_type=AnalysisOutput)
    res = agent.run_sync("Input text")
    assert res.output.summary == "Rescued by cloud"
```

---

## Step 4: Add Kubernetes Manifests and ExternalSecret

Add an `openrouter-secret.yaml` manifest in your app's directory to pull credentials from Vault:

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: openrouter-credentials
  namespace: my-new-app
  annotations:
    argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true
    argocd.argoproj.io/sync-wave: "1"
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault
    kind: ClusterSecretStore
  target:
    name: openrouter-credentials
    creationPolicy: Owner
  data:
  - secretKey: OPENROUTER_API_KEY
    remoteRef:
      key: openrouter
      property: api_key
```

In your `deployment.yaml` or `cronjob.yaml`, mount the secret and configure provider routing:

```yaml
            envFrom:
            - secretRef:
                name: openrouter-credentials
                optional: true
            env:
            - name: PRIMARY_LLM_PROVIDER
              value: "local"
            - name: FALLBACK_LLM_PROVIDER
              value: "openrouter"
            - name: LLM_BASE_URL
              value: "http://llama-server.llama.svc.cluster.local:8080/v1"
```

---

## Step 5: Configure Monorepo Dockerfile and CI Pipeline

In your `Dockerfile`, copy `packages/homelab-ai` into the build context and install with `--no-editable`:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

COPY packages/homelab-ai /build/packages/homelab-ai
COPY apps/my-new-app /build/apps/my-new-app
WORKDIR /build/apps/my-new-app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim-bookworm AS runner
WORKDIR /app

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

COPY --from=builder --chown=appuser:appgroup /build/apps/my-new-app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /build/apps/my-new-app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER appuser

ENTRYPOINT ["python", "-m", "my_new_app.main"]
```

In `.github/workflows/ci.yaml`, configure the Docker build action with `context: .`:

```yaml
      with:
        context: .
        file: ./apps/my-new-app/Dockerfile
```

---

## Step 6: Deploy and Verify Model Flipping

Verify that both linting and tests pass:

```bash
uv run ruff check
uv run ruff format --check
uv run ty check
uv run pytest
pre-commit run --all-files
```

After deploying via ArgoCD, toggle the primary model dynamically:

```bash
# Set OpenRouter Gemma 4 31B as primary
kubectl -n my-new-app set env deployment/my-new-app PRIMARY_LLM_PROVIDER=openrouter FALLBACK_LLM_PROVIDER=local

# Revert to local inference
kubectl -n my-new-app set env deployment/my-new-app PRIMARY_LLM_PROVIDER=local FALLBACK_LLM_PROVIDER=openrouter
```
