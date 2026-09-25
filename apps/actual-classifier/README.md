# Actual Classifier

AI-powered transaction classifier and tagger for Actual Budget, running locally on the homelab Kubernetes cluster.

## Features

- **Constrained Grammar Inference**: Guarantees only approved single-word categories and tags.
- **Payee Normalization**: Cleans cryptic bank strings (e.g., `TST*IDLY EXPRESS - MOUNT` -> `Idly Express`).
- **High Availability Routing**: Primary local inference via `llama-server` (Gemma 4) with automatic OpenRouter fallback via `packages/homelab-ai`.
- **Actual Budget Sync**: Direct integration using `actualpy` and Actual Budget API.
- **Deterministic Guardrails**: Validates outputs and prevents hallucinated categories.
