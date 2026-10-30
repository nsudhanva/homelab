# Actual Classifier

An AI classifier that sets the category and tag of transactions in Actual Budget. It runs as a CronJob each day at 03:00 (`America/Los_Angeles`) on the homelab Kubernetes cluster. Each run classifies a maximum of `BATCH_SIZE` transactions. The default is 25, and the CronJob sets 200. The `--limit` flag overrides `BATCH_SIZE` for one run.

## Features

- Schema-constrained output: The Pydantic enums `CategoryEnum` and `TagEnum` make sure that the model returns only approved single-word categories and tags.
- Payee normalization: The model changes unclear bank strings to clean payee names, for example `TST*IDLY EXPRESS - MOUNT` to `Idly Express`.
- Model fallback: The classifier uses Claude Haiku 5.5 first. If Claude Haiku 5.5 fails, it uses OpenRouter and then the local `llama-server` (Gemma 4) through `packages/homelab-ai`.
- Actual Budget sync: The classifier connects to Actual Budget with `actualpy`.
- Guardrails: The classifier validates each output and rejects categories that are not in the enum.
