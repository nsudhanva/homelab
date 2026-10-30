# Actual Classifier

An AI transaction classifier and tagger for Actual Budget. It runs as a daily CronJob (03:00) on the homelab Kubernetes cluster and classifies up to `BATCH_SIZE` transactions per run (default 25, the CronJob sets 200). The `--limit` flag overrides `BATCH_SIZE` for one run.

## Features

- **Schema-Constrained Output**: Pydantic enums make sure that the model gives only approved single-word categories and tags.
- **Payee Normalization**: Cleans unclear bank strings (e.g., `TST*IDLY EXPRESS - MOUNT` -> `Idly Express`).
- **High Availability Routing**: Uses Claude Haiku 5.5 first. If that fails, it uses OpenRouter and then the local `llama-server` (Gemma 4) through `packages/homelab-ai`.
- **Actual Budget Sync**: Connects directly with `actualpy` and the Actual Budget API.
- **Deterministic Guardrails**: Validates the outputs and stops hallucinated categories.
