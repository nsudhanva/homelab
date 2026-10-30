---
title: AI Configuration Reference
description: Environment variables, model providers, Vault paths, and CLI commands for the shared homelab-ai package.
keywords:
  - homelab-ai configuration
  - AI_MODEL
  - anthropic workspace id
  - openrouter fallback
sidebar:
  order: 40
---

# AI Configuration Reference

All AI workloads read the same settings through `homelab_ai.AISettings`. The cluster defaults are in `packages/homelab-ai/kustomize/kustomization.yaml`.

## Model specs

A model spec is `<provider>:<model>`. Only the first colon separates the provider, so OpenRouter slugs such as `openrouter:google/gemma-4-31b-it:free` work.

| Provider | Example spec | Credentials | Default timeout | Default HTTP retries |
|---|---|---|---|---|
| `local` | `local:gemma-4-e2b-it` | None | 120 s | 0 |
| `openrouter` | `openrouter:google/gemma-4-31b-it` | `OPENROUTER_API_KEY` | 60 s | 2 |
| `anthropic` | `anthropic:claude-haiku-5-5` | `ANTHROPIC_API_KEY`, optional `ANTHROPIC_WORKSPACE_ID` | 60 s | 2 |
| `openai` | `openai:gpt-5` | `OPENAI_API_KEY`, optional `OPENAI_BASE_URL` | 60 s | 2 |

Use `openai` with `OPENAI_BASE_URL` for any other OpenAI-compatible API. To add a provider with its own SDK, call `homelab_ai.register_provider`.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `AI_MODEL` | `local:gemma-4-e2b-it` | Primary model |
| `AI_FALLBACK_MODELS` | `openrouter:google/gemma-4-31b-it,anthropic:claude-haiku-5-5` | Comma-separated fallback chain. Set `none` to disable |
| `AI_ATTEMPTS` | `2` | Attempts per call when every model fails with a network, timeout, 429, or 5xx error |
| `AI_RETRY_BACKOFF_SECONDS` | `5` | Wait before the next attempt, multiplied by the attempt number |
| `AI_TIMEOUT_SECONDS` | Provider default | Request timeout for every provider |
| `AI_MAX_RETRIES` | Provider default | HTTP retries inside the provider client |
| `AI_TEMPERATURE` | Model default | Sampling temperature |
| `AI_MAX_TOKENS` | Model default | Output token limit |
| `LOCAL_LLM_BASE_URL` | `http://llama-server.llama.svc.cluster.local:8080/v1` | OpenAI-compatible URL of the local model server |
| `OPENROUTER_API_KEY` | None | OpenRouter key |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter URL |
| `ANTHROPIC_API_KEY` | None | Anthropic key |
| `ANTHROPIC_WORKSPACE_ID` | None | Sent as `anthropic-workspace-id`. Required for organization keys that are not scoped to one workspace |
| `ANTHROPIC_BASE_URL` | Anthropic default | Anthropic URL |
| `OPENAI_API_KEY` | None | Key for the `openai` provider |
| `OPENAI_BASE_URL` | OpenAI default | URL for the `openai` provider |

A model whose provider has no credentials is skipped and logged. The same chain therefore works on a workstation with only a local model and in the cluster with every key.

## Vault paths

| Vault path | Property | Environment variable |
|---|---|---|
| `kv/openrouter` | `api_key` | `OPENROUTER_API_KEY` |
| `kv/anthropic` | `api_key` | `ANTHROPIC_API_KEY` |
| `kv/anthropic` | `workspace_id` | `ANTHROPIC_WORKSPACE_ID` |

The `homelab-ai-credentials` ExternalSecret in `packages/homelab-ai/kustomize/externalsecret.yaml` reads these paths.

## Where to change models

| Scope | Where |
|---|---|
| Every AI workload | `literals` in `packages/homelab-ai/kustomize/kustomization.yaml` |
| One workload | An `env` entry in that CronJob or Deployment |
| One local run | Environment variables, for example `AI_MODEL=anthropic:claude-haiku-5-5 uv run python -m gmail_classifier.main --dry-run` |

## CLI

The `homelab-ai` command is installed with the package:

| Command | Result |
|---|---|
| `homelab-ai models` | Shows the chain and whether each provider has credentials |
| `homelab-ai ping` | Calls each model in the chain with a small structured prompt and prints the latency |
| `homelab-ai ping -m anthropic:claude-sonnet-5-5` | Calls only the given model. Repeat `-m` for more models |

In a container image, run `python -m homelab_ai.cli` instead of `homelab-ai`. The images copy the virtual environment from a build stage, so console scripts point to a path that does not exist.

## Workloads

| Workload | Tasks |
|---|---|
| `gmail-classifier` | `gmail-classifier` |
| `drive-organizer` | `drive-organizer`, `drive-organizer-triage` |
| `actual-classifier` | `actual-classifier` |
| `alert-summarizer` | `alert-summarizer` (overrides `AI_MAX_TOKENS` and `AI_TEMPERATURE`) |
