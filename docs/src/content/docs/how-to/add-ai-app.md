---
title: How to Add an AI Job with homelab-ai
description: Add an AI CronJob or service that uses the shared homelab-ai model chain, with local, OpenRouter, and Anthropic models and automatic fallback.
keywords:
  - add ai application
  - homelab-ai guide
  - pydantic-ai fallback
  - anthropic claude kubernetes
sidebar:
  order: 25
---

This guide adds an AI workload, for example `apps/receipt-reader`. The workload uses `packages/homelab-ai`. The package gives it the shared model chain, the provider credentials, the fallback, and the retries. For the list of settings, see [AI Configuration Reference](/reference/ai-configuration/).

## Step 1: Add the dependency

In `apps/receipt-reader/pyproject.toml`, add `homelab-ai` as a path dependency. The app gets `pydantic-ai` at runtime through `homelab-ai`. Add `pydantic-ai` to the dev group only. The tests import its test models.

```toml
[project]
dependencies = [
    "pydantic>=2.9.0",
    "homelab-ai",
]

[tool.uv.sources]
homelab-ai = { path = "../../packages/homelab-ai", editable = true }

[dependency-groups]
dev = [
    "pydantic-ai>=2.63.0",
    "pytest>=8.3.0",
    "ruff>=0.16.8",
    "ty>=0.0.81",
]
```

Run `uv lock && uv sync` in the app directory.

## Step 2: Define the task

An `AITask` is one structured LLM call. Give it a name, an output model, and instructions. Do not add model, URL, or API key settings to the app. `AITask` reads them from the environment.

```python
from homelab_ai import AITask, HomelabAIError, LLMConnectionError
from pydantic import BaseModel


class Receipt(BaseModel):
    merchant: str
    total: float
    confidence: float


class ReceiptReader:
    def __init__(self, task: AITask[Receipt] | None = None) -> None:
        self.task = task or AITask(
            name="receipt-reader",
            output_type=Receipt,
            instructions="Extract the merchant and the total from the receipt text.",
        )

    def read(self, text: str) -> Receipt | None:
        try:
            return self.task.run_sync(text)
        except HomelabAIError:
            return None
```

`run_sync` raises one of two errors when it cannot get a valid answer:

- `LLMConnectionError`: No model answered. Each model was unreachable, timed out, or was rate limited. A batch job can stop and let Kubernetes retry later.
- `LLMOutputError`: A model answered, but the answer did not agree with the output model. Send the item to manual review.

Use `await task.run(text)` in async code such as FastAPI handlers.

If many calls share the same text, such as a list of categories, pass the text as `stable_prefix`. Anthropic models then read it from the prompt cache at 0.1 times the input price.

```python
self.task.run_sync(receipt_text, stable_prefix=category_guide)
```

Do not hardcode input limits, such as the number of characters that you send. Add each limit to the `Settings` class of the app as a pydantic-settings field with an environment variable. Pass the values to the code that uses them. Set the defaults for the primary model. The local fallback model has an 8K token context.

## Step 3: Test with injected models

Pass `models` to inject Pydantic AI test models. The tests then run offline.

```python
from homelab_ai import AISettings, AITask
from pydantic_ai.models.test import TestModel


def test_reads_receipt() -> None:
    task = AITask(
        name="receipt-reader",
        output_type=Receipt,
        instructions="",
        settings=AISettings(_env_file=None, AI_ATTEMPTS=1),
        models=[
            TestModel(
                custom_output_args={
                    "merchant": "Safeway",
                    "total": 12.5,
                    "confidence": 0.9,
                }
            )
        ],
    )
    assert ReceiptReader(task).read("SAFEWAY $12.50").merchant == "Safeway"
```

The tests in `packages/homelab-ai` cover the fallback and retry behavior. Do not test this behavior again in each app.

## Step 4: Add the Kubernetes wiring

Add the shared component to `apps/receipt-reader/kustomization.yaml`. The component creates the `homelab-ai` ConfigMap (the model chain) and the `homelab-ai-credentials` ExternalSecret (the API keys from Vault) in the namespace of the app.

```yaml
namespace: receipt-reader
resources:
  - namespace.yaml
  - cronjob.yaml
components:
  - ../../packages/homelab-ai/kustomize
```

In the container spec, load the ConfigMap and the Secret:

```yaml
envFrom:
  - configMapRef:
      name: homelab-ai
  - secretRef:
      name: homelab-ai-credentials
```

To use a different model for this workload only, add an `env` entry. Values in `env` override values from `envFrom`.

```yaml
env:
  - name: AI_MODEL
    value: "local:gemma-4-e2b-it"
```

## Step 5: Add the Dockerfile and CI entry

Build from the repository root, so that the image can copy `packages/homelab-ai`. Copy `apps/gmail-classifier/Dockerfile` and change the app name. CI builds each image with the repository root as the context, so the root `.dockerignore` applies to each image. Do not add a `.dockerignore` in the app directory.

CI finds the app automatically. You do not change the workflow. CI treats each `apps/*/pyproject.toml` and `packages/*/pyproject.toml` as a Python project. If a `Dockerfile` is in the same directory, CI builds an image.

CI lints, type-checks, and tests the app when the app or `homelab-ai` changes. On `master`, CI also pushes `ghcr.io/nsudhanva/homelab-receipt-reader`.

## Step 6: Check the models before you push

Run the checks, and call the real models from your workstation:

```bash
uv run ruff check && uv run ruff format --check && uv run ty check && uv run pytest
LOCAL_LLM_BASE_URL=https://ai.sudhanva.me/v1 uv run homelab-ai models
LOCAL_LLM_BASE_URL=https://ai.sudhanva.me/v1 uv run homelab-ai ping
```

Push to Git. ArgoCD deploys the workload.
