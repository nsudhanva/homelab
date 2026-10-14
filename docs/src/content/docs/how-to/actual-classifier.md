---
title: How to Auto-Classify Actual Budget Transactions
description: Configure, benchmark, and deploy the AI transaction classifier for Actual Budget with the local Gemma 4 SLM and homelab-ai routing.
keywords:
  - actual budget classifier
  - pydantic ai actual budget
  - local llm finance classifier
  - transaction categorization
  - gemma 4 slm
sidebar:
  order: 21
---

# How to Auto-Classify Actual Budget Transactions

Use this guide to operate, configure, benchmark, and monitor the Actual Budget transaction classifier (`apps/actual-classifier/`).

## Architecture and Workflow

The classifier gives each imported bank transaction a category and a single-word tag:

- **Local inference first**: The local LLaMA server (`llama-server.llama.svc.cluster.local:8080/v1`) classifies the transactions with Google Gemma 4 (`gemma-4-e2b-it`).
- **Fallback**: If the local model has a high load or is temporarily unavailable, requests go to OpenRouter (`google/gemma-4-31b-it`). The shared `homelab-ai` router controls this fallback.
- **Taxonomy**: Pydantic schema validation limits the model to single-word categories (`Food`, `Transit`, `Shopping`, `Bills`, `Rent`, `Travel`, `Medical`, `Income`, `Savings`, `Transfer`) and single-word tags (`#Subscription`, `#Transit`, `#Medical`, `#Travel`, `#Income`, `#Bills`, `#Rent`, `#Transfer`, `#Unknown`).
- **Payee names**: The classifier changes raw POS strings (such as `TST*IDLY EXPRESS - MOUNT` or `ACH Withdrawal COMCAST-XFINITY`) into readable payee names (`Idly Express`, `Comcast`).
- **Confidence threshold**: If a prediction is below the configured confidence threshold (default `0.60`), the classifier tags it `#Unknown`. This prevents incorrect classification of ambiguous charges. If no tag applies (for example, groceries and general shopping), the note stays clean.
- **Scope**: The classifier processes only on-budget transactions that have no category or that have an `#Unknown` note. It skips transfers between accounts, off-budget tracking accounts (brokerage and retirement), split parents, and starting balances.
- **Amount sign**: A negative amount is an outflow and a positive amount is an inflow. If a positive amount comes from a merchant, the classifier records it as a refund in the category of that merchant.
- **Schedule**: A Kubernetes CronJob runs the classifier every day at 03:00 (`0 3 * * *`), after the Gmail (01:00) and Drive (02:00) jobs. The CronJob has concurrency control, and each pod is ephemeral and stops after the run. The `actual-classifier-push` CI job builds the image and publishes it to `ghcr.io/nsudhanva/homelab-actual-classifier`.

## Step 1: Review Configuration and Secrets

The classifier gets connection parameters from environment variables. It gets credentials from Vault through ExternalSecrets:

```yaml
ACTUAL_SERVER_URL: "http://actual-budget.actual-budget.svc.cluster.local:5006"
ACTUAL_BUDGET_NAME: "My Finances"
PRIMARY_LLM_PROVIDER: "local"
FALLBACK_LLM_PROVIDER: "openrouter"
LLM_BASE_URL: "http://llama-server.llama.svc.cluster.local:8080/v1"
LLM_MODEL: "gemma-4-e2b-it"
OPENROUTER_MODEL_NAME: "google/gemma-4-31b-it"
CONFIDENCE_THRESHOLD: "0.6"
BATCH_SIZE: "50"
```

The `actual-classifier-secrets` ExternalSecret reads `ACTUAL_PASSWORD` from Vault `kv/actual` (`password`) and `OPENROUTER_API_KEY` from `kv/openrouter` (`api_key`).

### Switch models or providers

Environment variables in `apps/actual-classifier/cronjob.yaml` control all provider routing. To switch, change one line in Git. ArgoCD applies the change on the next sync.

- To use OpenRouter as the primary model, set `PRIMARY_LLM_PROVIDER` to `openrouter` and `FALLBACK_LLM_PROVIDER` to `local`.
- To change the OpenRouter model, set `OPENROUTER_MODEL_NAME` to an OpenRouter model slug that supports structured output.
- To change the local model, set `LLM_MODEL` to the alias that `llama-server` serves.
- To disable the fallback, set `FALLBACK_LLM_PROVIDER` to `none`.

The classifier does not retry the local endpoint at the HTTP level (`LLM_MAX_RETRIES`, default `0`). Thus, a timeout sends the request to the fallback provider immediately. OpenRouter requests retry transient errors (`OPENROUTER_MAX_RETRIES`, default `2`).

Make sure that the ExternalSecret is synced in the namespace:

```bash
kubectl -n actual-classifier get externalsecret,secret
```

## Step 2: Run Hermetic Unit Tests and Verification

Unit tests cover all data models, Pydantic AI guardrails, and Actual Budget sync cycles:

```bash
cd apps/actual-classifier
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
```

Before you commit changes, make sure that all tests pass. Make sure that the static type checkers report zero diagnostics.

## Step 3: Execute Benchmark Evaluation

The classifier package has a standalone golden benchmark suite for household transaction domains:

```bash
cd apps/actual-classifier
uv run python -m actual_classifier.main --benchmark
```

The benchmark reports category accuracy, tag precision, payee normalization, and confidence scores for the test cases.

## Step 4: Preview Run with Dry-Run Mode

To examine pending unclassified transactions without changes to Actual Budget, run this command:

```bash
cd apps/actual-classifier
uv run python -m actual_classifier.main --dry-run --limit 10
```

The output shows the raw imported payees next to the proposed categories, tags, normalized payees, and confidence levels.

## Step 5: Trigger Scheduled CronJob Manually

To start a batch run on demand in the Kubernetes cluster, run these commands:

```bash
kubectl -n actual-classifier create job --from=cronjob/actual-classifier manual-actual-run
kubectl -n actual-classifier logs -f job/manual-actual-run
```

When the job completes, the changes sync immediately to Actual Budget. The category and subscription dashboards then show the changes.
