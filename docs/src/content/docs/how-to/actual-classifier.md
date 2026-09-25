---
title: How to Auto-Classify Actual Budget Transactions
description: Configure, benchmark, and deploy the AI-powered transaction classifier for Actual Budget using local Gemma 4 SLM and homelab-ai routing.
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

This problem-oriented guide explains how to operate, configure, benchmark, and monitor the automated Actual Budget Transaction Classifier (`apps/actual-classifier/`).

## Architecture and Workflow

The classifier automates categorization and single-word tagging for imported banking transactions:

- **Local Inference First**: Transactions are classified via the local LLaMA server (`llama-server.llama.svc.cluster.local:8080/v1`) running Google Gemma 4 (`gemma-4-e2b-it`).
- **Resilient Fallback**: If the local model is under heavy load or temporarily unavailable, requests fail over to OpenRouter (`google/gemma-4-31b-it`) managed transparently by the shared `homelab-ai` router.
- **Strict Taxonomy Enforcement**: The model is constrained via Pydantic schema validation to choose strictly from single-word categories (`Food`, `Transit`, `Shopping`, `Bills`, `Rent`, `Travel`, `Medical`, `Income`, `Savings`, `Transfer`) and single-word tags (`#Subscription`, `#Transit`, `#Medical`, `#Travel`, `#Income`, `#Bills`, `#Rent`, `#Transfer`, `#Unknown`).
- **Clean Merchant Standardization**: Raw POS strings (such as `TST*IDLY EXPRESS - MOUNT` or `ACH Withdrawal COMCAST-XFINITY`) are normalized to human-readable payees (`Idly Express`, `Comcast`).
- **Guardrails & Confidence Threshold**: Any prediction below the configured confidence threshold (default `0.60`) is tagged `#Unknown` to prevent misclassification of ambiguous charges.
- **Scheduled Sync**: Deployed as a Kubernetes CronJob running every two hours (`0 */2 * * *`) with concurrency control and ephemeral pod termination.

## Step 1: Review Configuration and Secrets

The classifier retrieves connection parameters from environment variables and credentials from Vault via ExternalSecrets:

```yaml
ACTUAL_SERVER_URL: "http://actual-budget.actual-budget.svc.cluster.local:5006"
ACTUAL_BUDGET_NAME: "My Finances"
PRIMARY_LLM_PROVIDER: "local"
FALLBACK_LLM_PROVIDER: "openrouter"
LLM_BASE_URL: "http://llama-server.llama.svc.cluster.local:8080/v1"
LLM_MODEL: "gemma-4-e2b-it"
CONFIDENCE_THRESHOLD: "0.6"
BATCH_SIZE: "50"
```

Verify that the external secret is synced in the namespace:

```bash
kubectl -n actual-classifier get externalsecret,secret
```

## Step 2: Run Hermetic Unit Tests and Verification

All data models, Pydantic AI guardrails, and Actual Budget sync cycles have comprehensive unit tests:

```bash
cd apps/actual-classifier
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
```

Ensure all tests pass and static type checkers report zero diagnostics before committing changes.

## Step 3: Execute Benchmark Evaluation

The classifier package includes a standalone golden benchmark suite covering household transaction domains:

```bash
cd apps/actual-classifier
uv run python -m actual_classifier.main --benchmark
```

The benchmark reports category accuracy, tag precision, payee normalization, and confidence scores across test cases.

## Step 4: Preview Run with Dry-Run Mode

To inspect pending unclassified transactions without committing changes to Actual Budget:

```bash
cd apps/actual-classifier
uv run python -m actual_classifier.main --dry-run --limit 10
```

The output displays raw imported payees alongside proposed categories, tags, normalized payees, and confidence levels.

## Step 5: Trigger Scheduled CronJob Manually

To trigger an on-demand batch run inside the Kubernetes cluster:

```bash
kubectl -n actual-classifier create job --from=cronjob/actual-classifier manual-actual-run
kubectl -n actual-classifier logs -f job/manual-actual-run
```

Once completed, changes are synced immediately to Actual Budget and reflected in category and subscription dashboards.
