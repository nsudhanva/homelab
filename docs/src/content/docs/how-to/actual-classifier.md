---
title: How to Auto-Classify Actual Budget Transactions
description: Configure, benchmark, and run the AI transaction classifier for Actual Budget, which uses Claude Haiku through the homelab-ai model chain.
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

Use this guide to configure, benchmark, run, and monitor the Actual Budget transaction classifier (`apps/actual-classifier/`).

## Architecture and Workflow

The classifier gives each imported bank transaction a category and a one-word tag.

- Model chain: Claude Haiku 5.5 classifies the transactions. If it is not available, requests go to OpenRouter (`google/gemma-4-31b-it`) and then to the local model (`gemma-4-e2b-it`). The shared `homelab-ai` chain controls this fallback.
- Taxonomy: Pydantic schema validation limits the model to one-word categories (`Food`, `Transit`, `Shopping`, `Bills`, `Rent`, `Travel`, `Medical`, `Income`, `Savings`, `Transfer`). It also limits the model to one-word tags (`#Subscription`, `#Transit`, `#Medical`, `#Travel`, `#Income`, `#Bills`, `#Rent`, `#Transfer`, `#Unknown`).
- Payee names: The classifier changes raw POS strings into readable payee names. For example, `TST*IDLY EXPRESS - MOUNT` becomes `Idly Express`, and `ACH Withdrawal COMCAST-XFINITY` becomes `Comcast`.
- Confidence threshold: If the confidence of a prediction is below the threshold (default `0.60`), the classifier tags the transaction `#Unknown`. This prevents wrong categories on unclear charges. If no tag applies, for example on groceries or general shopping, the classifier writes no tag in the note.
- Scope: The classifier processes only on-budget transactions that have no category or that have an `#Unknown` note. It skips transfers between accounts, off-budget accounts (brokerage and retirement), split parents, and starting balances.
- Amount sign: A negative amount is an outflow, and a positive amount is an inflow. The classifier records a positive amount from a merchant as a refund in the category of that merchant.
- Schedule: A Kubernetes CronJob runs the classifier each day at 03:00 (`0 3 * * *`), after the Gmail (01:00) and Drive (02:00) jobs. The CronJob uses `concurrencyPolicy: Forbid`, and each pod stops after its run.
- Image: The `push (actual-classifier)` CI job builds the image and pushes it to `ghcr.io/nsudhanva/homelab-actual-classifier`.

## Step 1: Review the Configuration and Secrets

The classifier reads its connection settings from environment variables. It reads its credentials from Vault through an ExternalSecret.

```yaml
ACTUAL_SERVER_URL: "http://actual-budget.actual-budget.svc.cluster.local:5006"
ACTUAL_BUDGET_NAME: "My Finances"
CONFIDENCE_THRESHOLD: "0.6"
BATCH_SIZE: "200"
```

`BATCH_SIZE` is the maximum number of transactions that one run classifies. The `Settings` default is `25`, and the CronJob sets `200`. The `--limit` flag overrides `BATCH_SIZE` for one run.

The `actual-classifier-secrets` ExternalSecret reads `ACTUAL_PASSWORD` from Vault `kv/actual` (property `password`).

### Change the model or the provider

The classifier uses the shared `homelab-ai` model chain from the `homelab-ai` ConfigMap and the `homelab-ai-credentials` Secret. To use a different model for this job only, add an `AI_MODEL` entry to `env` in `apps/actual-classifier/cronjob.yaml`. For the variables and the providers, see [AI Configuration Reference](/reference/ai-configuration/).

Make sure that the ExternalSecret is synced in the namespace:

```bash
kubectl -n actual-classifier get externalsecret,secret
```

## Step 2: Run the Unit Tests and the Checks

The unit tests cover the data models, the Pydantic AI guardrails, and the Actual Budget sync cycle. They do not call external services.

```bash
cd apps/actual-classifier
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
```

Before you commit, make sure that all tests pass. Make sure that the type checker reports zero diagnostics.

## Step 3: Run the Benchmark

The classifier package has a golden benchmark of household transactions:

```bash
cd apps/actual-classifier
uv run python -m actual_classifier.main --benchmark
```

The benchmark reports the category accuracy, the tag precision, the payee normalization, and the confidence scores for the test cases.

## Step 4: Preview a Run with Dry-Run Mode

To see the unclassified transactions without changes to Actual Budget, run this command. `--limit 10` overrides `BATCH_SIZE` for this run.

```bash
cd apps/actual-classifier
uv run python -m actual_classifier.main --dry-run --limit 10
```

The output shows each raw imported payee with the proposed category, tag, payee name, and confidence.

## Step 5: Start the CronJob Manually

To start a run in the cluster, run these commands:

```bash
kubectl -n actual-classifier create job --from=cronjob/actual-classifier manual-actual-run
kubectl -n actual-classifier logs -f job/manual-actual-run
```

The job writes the changes to Actual Budget. The category and subscription dashboards then show the changes.
