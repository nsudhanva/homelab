---
title: How to Add an AI Job with homelab-ai
description: Add a new AI CronJob or service that uses the shared homelab-ai model chain, with local, OpenRouter, and Anthropic models and automatic fallback.
keywords:
  - add ai application
  - homelab-ai guide
  - pydantic-ai fallback
  - anthropic claude kubernetes
sidebar:
  order: 25
---

# How to Add an AI Job with homelab-ai

This guide adds a new AI workload, for example `apps/receipt-reader`. The workload uses `packages/homelab-ai`, so it gets the shared model chain, provider credentials, fallback, and retries without extra code. For the list of settings, see [AI Configuration Reference](/reference/ai-configuration/).

## Step 1: Add the dependency

In `apps/receipt-reader/pyproject.toml`, add `homelab-ai` as a path dependency:

```toml
[project]
dependencies = [
    "pydantic-ai>=2.63.0",
    "homelab-ai",
]

[tool.uv.sources]
homelab-ai = { path = "../../packages/homelab-ai", editable = true }
```

Then run `uv lock && uv sync` in the app directory.

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

- `LLMConnectionError`: Every model was unreachable, timed out, or rate limited. Batch jobs can stop and let Kubernetes retry later.
- `LLMOutputError`: A model answered, but the answer did not match the output model. Send the item to manual review.

Use `await task.run(text)` in async code such as FastAPI handlers.

If many calls share the same text, such as a list of categories, pass it as `stable_prefix`. Anthropic models then read it from the prompt cache at 0.1 times the input price:

```python
self.task.run_sync(receipt_text, stable_prefix=category_guide)
```

Do not hardcode input limits such as the number of characters you send. Add them to the `Settings` class of the app as pydantic-settings fields with an environment variable, and pass the values to the code that uses them. Size the defaults for the primary model. The local fallback model has an 8K token context.

## Step 3: Test with injected models

Pass `models` to inject Pydantic AI test models. Tests then run offline:

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

Fallback and retry behavior is tested once in `packages/homelab-ai`. Do not test it again in each app.

## Step 4: Add the Kubernetes wiring

Add the shared component to `apps/receipt-reader/kustomization.yaml`. The component creates the `homelab-ai` ConfigMap (model chain) and the `homelab-ai-credentials` ExternalSecret (API keys from Vault) in the namespace of the app:

```yaml
namespace: receipt-reader
resources:
  - namespace.yaml
  - cronjob.yaml
components:
  - ../../packages/homelab-ai/kustomize
```

In the container spec, load both:

```yaml
envFrom:
  - configMapRef:
      name: homelab-ai
  - secretRef:
      name: homelab-ai-credentials
```

To use a different model for this workload only, add an `env` entry. Values in `env` override `envFrom`:

```yaml
env:
  - name: AI_MODEL
    value: "local:gemma-4-e2b-it"
```

## Step 5: Add the Dockerfile and CI entry

Build from the repository root so the image can copy `packages/homelab-ai`. Copy `apps/gmail-classifier/Dockerfile` and change the app name.

CI finds the app without changes to the workflow. Every `apps/*/pyproject.toml` and `packages/*/pyproject.toml` is a Python project, and a `Dockerfile` next to it means that CI builds an image.

CI then lints, type-checks, and tests the app when the app or `homelab-ai` changes. On `master`, CI also pushes `ghcr.io/nsudhanva/homelab-receipt-reader`.

## Step 6: Check the models before you push

Run the checks and call the real models from your workstation:

```bash
uv run ruff check && uv run ruff format --check && uv run ty check && uv run pytest
LOCAL_LLM_BASE_URL=https://ai.sudhanva.me/v1 uv run homelab-ai models
LOCAL_LLM_BASE_URL=https://ai.sudhanva.me/v1 uv run homelab-ai ping
```

Push to Git. ArgoCD deploys the workload.
