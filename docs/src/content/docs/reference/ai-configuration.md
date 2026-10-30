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

A model spec is `<provider>:<model>`. The first colon separates the provider from the model. Thus, a model name can contain a colon, for example `openrouter:google/gemma-4-31b-it:free`.

| Provider | Example spec | Credentials | Default timeout | Default HTTP retries |
|---|---|---|---|---|
| `local` | `local:gemma-4-e2b-it` | None | 120 s | 0 |
| `openrouter` | `openrouter:google/gemma-4-31b-it` | `OPENROUTER_API_KEY` | 60 s | 2 |
| `anthropic` | `anthropic:claude-haiku-5-5` | `ANTHROPIC_API_KEY`, optional `ANTHROPIC_WORKSPACE_ID` | 60 s | 2 |
| `openai` | `openai:gpt-5` | `OPENAI_API_KEY`, optional `OPENAI_BASE_URL` | 60 s | 2 |

For a different OpenAI-compatible API, use `openai` with `OPENAI_BASE_URL`. To add a provider with its own SDK, call `homelab_ai.register_provider`.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `AI_MODEL` | `anthropic:claude-haiku-5-5` | Primary model |
| `AI_FALLBACK_MODELS` | `openrouter:google/gemma-4-31b-it,local:gemma-4-e2b-it` | Comma-separated fallback chain. Set `none` to turn off the fallback |
| `AI_ATTEMPTS` | `2` | Attempts per call when every model fails with a network, timeout, 429, or 5xx error |
| `AI_RETRY_BACKOFF_SECONDS` | `5` | Wait before the next attempt, multiplied by the attempt number |
| `AI_TIMEOUT_SECONDS` | Provider default | Request timeout for every provider |
| `AI_MAX_RETRIES` | Provider default | HTTP retries inside the provider client |
| `AI_EFFORT` | Model default (`medium` on Haiku 5.5) | Thinking effort: `low`, `medium`, `high`, `xhigh`, or `max`. Providers without effort ignore it |
| `AI_TEMPERATURE` | Model default | Sampling temperature. Haiku 5.5 does not accept it, so only the fallback models use it |
| `AI_MAX_TOKENS` | Model maximum | Output token limit. Thinking counts toward this limit |
| `LOCAL_LLM_BASE_URL` | `http://llama-server.llama.svc.cluster.local:8080/v1` | OpenAI-compatible URL of the local model server |
| `OPENROUTER_API_KEY` | None | OpenRouter key |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter URL |
| `ANTHROPIC_API_KEY` | None | Anthropic key |
| `ANTHROPIC_WORKSPACE_ID` | None | Sent as `anthropic-workspace-id`. Required for organization keys that are not scoped to one workspace |
| `ANTHROPIC_BASE_URL` | Anthropic default | Anthropic URL |
| `OPENAI_API_KEY` | None | Key for the `openai` provider |
| `OPENAI_BASE_URL` | OpenAI default | URL for the `openai` provider |

`homelab-ai` skips and logs each model whose provider has no credentials. Thus, the same chain works on a workstation with only a local model and in the cluster with all keys.

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
| One local run | Environment variables, for example `AI_MODEL=local:gemma-4-e2b-it uv run python -m gmail_classifier.main --dry-run` |

## CLI

The package installs the `homelab-ai` command.

| Command | Result |
|---|---|
| `homelab-ai models` | Shows the chain and whether each provider has credentials |
| `homelab-ai ping` | Calls each model in the chain with a small structured prompt and prints the latency |
| `homelab-ai ping -m anthropic:claude-sonnet-5-5` | Calls only the given model. Repeat `-m` for more models |

In a container image, run `python -m homelab_ai.cli`. Do not run `homelab-ai`. The images copy the virtual environment from a build stage, so the console scripts point to a path that does not exist.

## Workloads

| Workload | Tasks |
|---|---|
| `gmail-classifier` | `gmail-classifier` |
| `drive-organizer` | `drive-organizer`, `drive-organizer-triage` |
| `actual-classifier` | `actual-classifier` |
| `alert-summarizer` | `alert-summarizer` |

## App input limits

Each app keeps its limits in its pydantic-settings `Settings` class. To change a limit for one workload, add an `env` entry to its CronJob. For the Gmail and Drive CronJobs, change `scripts/generate-account-manifests.py` and run it again.

| Workload | Variable | Default | Purpose |
|---|---|---|---|
| `gmail-classifier` | `MAX_BODY_CHARS` | `12000` | Characters of the cleaned email body sent to the model |
| `gmail-classifier` | `CONCURRENCY` | `4` | Emails classified at the same time |
| `drive-organizer` | `MAX_DOWNLOAD_BYTES` | `20000000` | Bytes downloaded from each file for inspection |
| `drive-organizer` | `MAX_DOCUMENT_CHARS` | `24000` | Characters of document text sent to the model |
| `drive-organizer` | `PDF_MAX_PAGES` | `10` | PDF pages whose text is extracted |
| `drive-organizer` | `TRIAGE_MAX_FILES` | `200` | Files listed in a folder manifest for folder triage |
| `actual-classifier` | `BATCH_SIZE` | `25` (CronJob: `200`) | Transactions classified in one run |
