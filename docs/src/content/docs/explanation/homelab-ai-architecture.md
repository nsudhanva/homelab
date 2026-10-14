---
title: High-Availability AI Model Routing and Fallback Architecture
description: The shared homelab-ai framework, Pydantic AI FallbackModel routing, and the Vault GitOps flow that keeps secrets out of Git.
keywords:
  - homelab-ai
  - pydantic-ai fallback
  - openrouter gemma 4
  - llama-server kubernetes
  - gitops ai architecture
sidebar:
  order: 50
---

# High-Availability AI Model Routing and Fallback Architecture

In this bare-metal Kubernetes homelab, workloads use local GPU-accelerated small language models (SLMs). These models run on bare-metal inference servers (`llama-server` with Google Gemma 4 E2B). GPU servers can have hardware stalls, out-of-memory (OOM) events, or high queue latency during batch jobs.

To keep the AI applications available when these failures occur, all of them share one architecture: `packages/homelab-ai`.

---

## Architectural Principles

The AI routing architecture follows these principles:

- Single Responsibility Principle (SRP): Model provider builders create specific clients. Configuration classes validate environment schemas. The router controls the failover policies.
- Open-Closed Principle (OCP): You can register new inference providers (for example, Anthropic, Google Gemini, Ollama, vLLM) in the runtime registry. You do not have to change the consumer microservices.
- Dependency Inversion Principle (DIP): Workloads depend on the abstract `ModelRouter` and the Pydantic AI `Model` interface. They do not depend on low-level HTTP clients.
- GitOps with no secret exposure: Cloud API keys are never in Git repositories, container layers, or unencrypted ConfigMaps. All secrets are in HashiCorp Vault.

---

## Core Components

### Provider Strategy

Provider builders implement `BaseProviderBuilder`. Each builder makes a configured Pydantic AI `Model` instance:

- `LocalOpenAIProviderBuilder`: Targets the bare-metal K3s `llama-server` (`gemma-4-e2b-it`).
- `OpenRouterProviderBuilder`: Targets the OpenRouter cloud gateway (`google/gemma-4-31b-it`). It adds the standard attribution headers (`HTTP-Referer`, `X-Title`).
- `CustomModelProviderBuilder`: Adds mock or test models for hermetic unit tests.

### ModelRouter and Pydantic AI FallbackModel

The `ModelRouter` reads the active provider configuration:

- If `fallback_provider` is `openrouter` and credentials exist, the router makes this model:
  `FallbackModel(primary_model, fallback_model, fallback_on=(ModelAPIError,))`
- The `ModelAPIError` condition catches network timeouts, dropped connections, and the HTTP status codes `429`, `500`, `502`, `503`, and `504`.
- If the primary endpoint fails, Pydantic AI sends the inference to the fallback model on the first request attempt. Jobs do not restart and pipelines do not crash.

### Symmetrical Model Toggling

In each application, the operator can change the model with standard environment variables:

- `PRIMARY_LLM_PROVIDER`: Set to `local` (default) or `openrouter`.
- `FALLBACK_LLM_PROVIDER`: Set to `openrouter` (default), `local`, or `none`.

To move primary inference to the cloud during local maintenance, change one variable:

```bash
kubectl -n gmail-classifier set env cronjob/gmail-classifier PRIMARY_LLM_PROVIDER=openrouter FALLBACK_LLM_PROVIDER=local
```

---

## HashiCorp Vault Secret Flow

The secret is in HashiCorp Vault at `kv/openrouter`, in the `api_key` field. You write it there one time.

The External Secrets Operator (ESO) syncs this secret to all AI namespaces. It uses a shared `ClusterSecretStore`:

- `drive-organizer` $\rightarrow$ `openrouter-credentials`
- `gmail-classifier` $\rightarrow$ `openrouter-credentials`
- `monitoring` $\rightarrow$ `openrouter-credentials`

Each workload mounts `openrouter-credentials` with `optional: true`. If Vault is sealed or the key is not present, the applications continue to run on the local SLM. Pod initialization does not fail.
