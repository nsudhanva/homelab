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

The homelab runs a small language model (`gemma-4-e2b-it`) on a GTX 1050 Ti through `llama-server`. The local model is free and private, but it is slow, it has an 8K token context, and it can stall or run out of memory during batch jobs. Claude Haiku 5.5 has a 1M token context, and is fast, accurate, and cheap ($0.10 per million input tokens for prompts up to 100K tokens). The AI jobs use Haiku first and keep OpenRouter and the local model as fallbacks, through one shared package, `packages/homelab-ai`. The llama.cpp web UI at `ai.sudhanva.me` still uses only the local model.

## One chain for every workload

Before `homelab-ai` 0.2, each app declared its own LLM settings with different names, and each app had its own retry loop. Now the model chain is one setting:

```text
AI_MODEL=anthropic:claude-haiku-5-5
AI_FALLBACK_MODELS=openrouter:google/gemma-4-31b-it,local:gemma-4-e2b-it
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

- In one request, the `FallbackModel` tries the next model in the chain when a model returns an API error, or when its output fails validation. A model that returns bad JSON is therefore rescued by the next model.
- If every model fails with a network error, a timeout, a 429, or a 5xx status, `AITask` waits and tries again, up to `AI_ATTEMPTS` times.
- Then `AITask` raises `LLMConnectionError` for infrastructure failures, or `LLMOutputError` for answers that are not valid. Apps decide what to do. The Gmail classifier stops the batch on `LLMConnectionError` and sends the email to review on `LLMOutputError`.

`AITask` decides whether a failure is transient from the exception type and the HTTP status. It does not search error messages for words.

## Claude features

`homelab-ai` uses these Claude features when an Anthropic model runs:

- Prompt caching: The Anthropic builder marks the instructions and the tool definitions for caching. `AITask.run` and `AITask.run_sync` also take `stable_prefix`, text that many calls share, such as the label guide of the Gmail classifier. The task puts a cache breakpoint after this text. Cache reads cost 0.1 times the input price. OpenRouter ignores the breakpoint, and llama.cpp reuses the same prefix from its own cache.
- Adaptive thinking: Haiku 5.5 thinks by default at `medium` effort. `AI_EFFORT` sets the effort for every task. Pydantic AI then uses native structured output, so the model can think before it answers. Other providers ignore the setting.
- No sampling settings: Haiku 5.5 rejects `temperature`, `top_p`, and `top_k`. Pydantic AI removes them from Anthropic requests, so `AI_TEMPERATURE` affects only the fallback models.

## Input limits

The local model limited how much text each job could send. The apps now keep their input limits in their pydantic-settings `Settings` class, with sizes for Haiku, and you can change each limit with an environment variable. For the values, see [AI Configuration Reference](/reference/ai-configuration/#app-input-limits). A long input can be larger than the 8K context of the local model. When this happens, the local model fails as the last model in the chain, and the app handles the error.

## Thread safety

Provider HTTP clients bind to the event loop that first uses them. `run_sync` runs one event loop for each worker thread. `AITask` therefore makes one agent for each thread, so the Gmail and Drive worker pools can share one task.

## Secrets

API keys are only in HashiCorp Vault. The component contains an ExternalSecret that syncs `kv/openrouter` and `kv/anthropic` into a `homelab-ai-credentials` Secret in each AI namespace. If a key is missing, `homelab-ai` skips that provider and logs a message. The workload continues with the models that remain.
