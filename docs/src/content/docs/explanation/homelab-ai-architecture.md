---
title: AI Model Routing and Fallback Architecture
description: Why every homelab AI workload shares one model chain, how fallback and retries work, and how secrets reach the workloads.
keywords:
  - homelab-ai
  - pydantic-ai fallback
  - anthropic claude
  - llama-server kubernetes
  - gitops ai architecture
sidebar:
  order: 50
---

# AI Model Routing and Fallback Architecture

The homelab runs a small language model (`gemma-4-e2b-it`) on a GTX 1050 Ti through `llama-server`. The local model is free and private, but it is slow, and it can stall or run out of memory during batch jobs. Cloud models are fast and accurate, but they cost money. The AI workloads use both through one shared package, `packages/homelab-ai`.

## One chain for every workload

Before `homelab-ai` 0.2, each app declared its own LLM settings with different names, and each app had its own retry loop. Now the model chain is one setting:

```text
AI_MODEL=local:gemma-4-e2b-it
AI_FALLBACK_MODELS=openrouter:google/gemma-4-31b-it,anthropic:claude-haiku-5-5
```

The kustomize component in `packages/homelab-ai/kustomize` puts these values in a ConfigMap in each AI namespace. A change to the component changes every workload. The ConfigMap name has a content hash, so a change also restarts Deployments such as `alert-summarizer`. CronJobs use the new values on their next run.

## Task, model, and provider

The package has three layers:

- `AITask`: One structured LLM call with a name, an output model, and instructions. Apps use only this layer.
- Model chain: `build_routed_model` turns the specs into Pydantic AI models and wraps them in a `FallbackModel`.
- Providers: A registry maps a provider name (`local`, `openrouter`, `anthropic`, `openai`) to a builder and to a credential check.

Apps do not import provider SDKs, read API keys, or know which models exist. To add a provider, register a builder. You do not have to change the apps.

## Failure handling

Failures go through three levels:

- In one request, the `FallbackModel` tries the next model in the chain when a model returns an API error, or when its output fails validation. A small local model that returns bad JSON is therefore rescued by a larger cloud model.
- If every model fails with a network error, a timeout, a 429, or a 5xx status, `AITask` waits and tries again, up to `AI_ATTEMPTS` times.
- Then `AITask` raises `LLMConnectionError` for infrastructure failures, or `LLMOutputError` for answers that are not valid. Apps decide what to do. The Gmail classifier stops the batch on `LLMConnectionError` and sends the email to review on `LLMOutputError`.

`AITask` decides whether a failure is transient from the exception type and the HTTP status. It does not search error messages for words.

## Thread safety

Provider HTTP clients bind to the event loop that first uses them. `run_sync` runs one event loop for each worker thread. `AITask` therefore makes one agent for each thread, so the Gmail and Drive worker pools can share one task.

## Secrets

API keys are only in HashiCorp Vault. The component contains an ExternalSecret that syncs `kv/openrouter` and `kv/anthropic` into a `homelab-ai-credentials` Secret in each AI namespace. If a key is missing, `homelab-ai` skips that provider and logs a message. The workload continues with the models that remain.
