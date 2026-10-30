---
title: How to Auto-Classify Actual Budget Transactions
description: Configure, benchmark, and deploy the AI transaction classifier for Actual Budget with Claude Haiku and homelab-ai routing.
keywords:
  - actual budget classifier
  - pydantic ai actual budget
  - llm finance classifier
  - transaction categorization
  - claude haiku
sidebar:
  order: 21
---

# How to Auto-Classify Actual Budget Transactions

Use this guide to operate, configure, benchmark, and monitor the Actual Budget transaction classifier (`apps/actual-classifier/`).

## Architecture and Workflow

The classifier gives each imported bank transaction a category and a single-word tag:

- **Model chain**: Claude Haiku 5.5 classifies the transactions. If it is unavailable, requests go to OpenRouter (`google/gemma-4-31b-it`) and then to the local model (`gemma-4-e2b-it`). The shared `homelab-ai` chain controls this fallback.
- **Taxonomy**: Pydantic schema validation limits the model to single-word categories (`Food`, `Transit`, `Shopping`, `Bills`, `Rent`, `Travel`, `Medical`, `Income`, `Savings`, `Transfer`) and single-word tags (`#Subscription`, `#Transit`, `#Medical`, `#Travel`, `#Income`, `#Bills`, `#Rent`, `#Transfer`, `#Unknown`).
- **Payee names**: The classifier changes raw POS strings (such as `TST*IDLY EXPRESS - MOUNT` or `ACH Withdrawal COMCAST-XFINITY`) into readable payee names (`Idly Express`, `Comcast`).
- **Confidence threshold**: If a prediction is below the configured confidence threshold (default `0.60`), the classifier tags it `#Unknown`. This prevents incorrect classification of ambiguous charges. If no tag applies (for example, groceries and general shopping), the note stays clean.
- **Scope**: The classifier processes only on-budget transactions that have no category or that have an `#Unknown` note. It skips transfers between accounts, off-budget tracking accounts (brokerage and retirement), split parents, and starting balances.
- **Amount sign**: A negative amount is an outflow and a positive amount is an inflow. If a positive amount comes from a merchant, the classifier records it as a refund in the category of that merchant.
- **Schedule**: A Kubernetes CronJob runs the classifier every day at 03:00 (`0 3 * * *`), after the Gmail (01:00) and Drive (02:00) jobs. The CronJob has concurrency control, and each pod is ephemeral and stops after the run. The `push (actual-classifier)` CI job builds the image and publishes it to `ghcr.io/nsudhanva/homelab-actual-classifier`.

## Step 1: Review Configuration and Secrets

The classifier gets connection parameters from environment variables. It gets credentials from Vault through ExternalSecrets:

```yaml
ACTUAL_SERVER_URL: "http://actual-budget.actual-budget.svc.cluster.local:5006"
ACTUAL_BUDGET_NAME: "My Finances"
CONFIDENCE_THRESHOLD: "0.6"
BATCH_SIZE: "200"
```

`BATCH_SIZE` is the maximum number of transactions that one run classifies. The `Settings` default is `25`, and the CronJob sets `200`. The `--limit` flag overrides it for one run. Without `--limit`, the run uses `BATCH_SIZE`.

The `actual-classifier-secrets` ExternalSecret reads `ACTUAL_PASSWORD` from Vault `kv/actual` (`password`).

### Switch models or providers

The classifier uses the shared `homelab-ai` model chain from the `homelab-ai` ConfigMap and the `homelab-ai-credentials` Secret. To use another model for this job only, add an `AI_MODEL` entry to `env` in `apps/actual-classifier/cronjob.yaml`. For the variables and the providers, see [AI Configuration Reference](/reference/ai-configuration/).

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

To examine pending unclassified transactions without changes to Actual Budget, run this command. `--limit 10` overrides `BATCH_SIZE` for this run:

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
