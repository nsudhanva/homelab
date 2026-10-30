---
title: AI Model Routing and Fallback Architecture
description: How every homelab AI workload uses one shared model chain, how fallback and retries work, and how the API keys get to the workloads.
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

All AI jobs in the homelab use one shared package, `packages/homelab-ai`. The package sends each request to Claude Haiku 5.5. If Claude Haiku 5.5 fails, the package tries OpenRouter and then the local model.

The local model is `gemma-4-e2b-it`. It runs on a GTX 1050 Ti through `llama-server`. It costs nothing and keeps the data in the cluster, but it is slow and has an 8K token context. It can also stall or run out of memory during batch jobs. The llama.cpp web UI at `ai.sudhanva.me` uses only the local model.

Claude Haiku 5.5 is fast and accurate, and it has a 1M token context. It costs $0.10 per million input tokens for prompts up to 100K tokens.

## One chain for every workload

The model chain is one setting:

```text
AI_MODEL=anthropic:claude-haiku-5-5
AI_FALLBACK_MODELS=openrouter:google/gemma-4-31b-it,local:gemma-4-e2b-it
```

The kustomize component in `packages/homelab-ai/kustomize` puts these values in a ConfigMap in each AI namespace. A change to the component changes every workload. The ConfigMap name has a content hash, so a change also restarts Deployments such as `alert-summarizer`. CronJobs use the new values on their next run.

## Task, model, and provider

The package has three layers:

- `AITask`: One structured LLM call with a name, an output model, and instructions. Apps use only this layer.
- Model chain: `build_routed_model` turns the specs into Pydantic AI models and puts them in a `FallbackModel`.
- Providers: A registry maps each provider name (`local`, `openrouter`, `anthropic`, `openai`) to a builder and to a credential check.

Apps do not import provider SDKs, read API keys, or know which models exist. To add a provider, register a builder. The apps need no change.

## Failure handling

`homelab-ai` handles failures at three levels:

- In one request, the `FallbackModel` tries the next model in the chain when a model returns an API error. It also tries the next model when the output fails validation. Thus, when one model returns JSON that is not valid, the next model can answer.
- If every model fails with a network error, a timeout, a 429, or a 5xx status, `AITask` waits and tries again. It tries a maximum of `AI_ATTEMPTS` times.
- After the last attempt, `AITask` raises `LLMConnectionError` for an infrastructure failure, or `LLMOutputError` for an answer that is not valid. Each app decides what to do. The Gmail classifier stops the batch on `LLMConnectionError`, and it sends the email to review on `LLMOutputError`.

`AITask` uses the exception type and the HTTP status to find transient failures. It does not search the error messages for words.

## Claude features

`homelab-ai` uses these Claude features when an Anthropic model runs:

- Prompt caching: The Anthropic builder marks the instructions and the tool definitions for caching. `AITask.run` and `AITask.run_sync` also accept `stable_prefix`, which is text that many calls share, for example the label guide of the Gmail classifier. The task puts a cache breakpoint after this text. A cache read costs 0.1 times the input price. OpenRouter ignores the breakpoint, and llama.cpp reuses the same prefix from its own cache.
- Adaptive thinking: Haiku 5.5 thinks at `medium` effort by default. `AI_EFFORT` sets the effort for every task. When thinking is on, Pydantic AI uses native structured output, so the model can think before it answers. Other providers ignore the setting.
- Sampling settings: Haiku 5.5 rejects `temperature`, `top_p`, and `top_k`. Pydantic AI removes them from Anthropic requests, so `AI_TEMPERATURE` has an effect only on the fallback models.

## Input limits

Each app keeps its input limits in its pydantic-settings `Settings` class. The default sizes fit Haiku, and an environment variable can change each limit. For the values, refer to [AI Configuration Reference](/reference/ai-configuration/#app-input-limits). A long input can be larger than the 8K context of the local model. In this case, the local model fails as the last model in the chain, and the app handles the error.

## Thread safety

A provider HTTP client binds to the event loop that uses it first. `run_sync` runs one event loop for each worker thread. Thus, `AITask` makes one agent for each thread, and the Gmail and Drive worker pools can share one task.

## Secrets

The API keys are only in HashiCorp Vault. The component contains an ExternalSecret that syncs `kv/openrouter` and `kv/anthropic` into a `homelab-ai-credentials` Secret in each AI namespace. If a key is missing, `homelab-ai` skips that provider and logs a message. The workload continues with the remaining models.
