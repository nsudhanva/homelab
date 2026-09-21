---
title: High-Availability AI Model Routing and Fallback Architecture
description: Understanding the shared homelab-ai framework, Pydantic AI FallbackModel routing, and zero-secret Vault GitOps architecture.
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

In an autonomous bare-metal Kubernetes homelab, workloads rely on local GPU-accelerated small language models (SLMs) running on bare-metal inference servers (`llama-server` running Google Gemma 4 E2B). However, GPU servers can encounter hardware stalls, out-of-memory (OOM) events, or high queuing latency during batch jobs.

To guarantee zero downtime and 100% operational resilience, all homelab AI applications share a common, extensible architecture: **`packages/homelab-ai`**.

---

## Architectural Principles

The AI routing architecture adheres to senior staff software engineering standards:

- **Single Responsibility Principle (SRP)**: Model provider builders instantiate specific clients, configuration classes validate environment schemas, and the router orchestrates failover policies.
- **Open-Closed Principle (OCP)**: New inference providers (e.g. Anthropic, Google Gemini, Ollama, vLLM) can be registered into the runtime registry without modifying existing consumer microservices.
- **Dependency Inversion Principle (DIP)**: Workloads depend on the abstract `ModelRouter` and Pydantic AI `Model` interface rather than low-level HTTP clients.
- **100% GitOps & Zero-Secret Exposure**: Cloud API keys never enter Git repositories, container layers, or unencrypted ConfigMaps. All secrets reside in HashiCorp Vault.

---

## Core Components

### 1. The Provider Strategy

Provider builders implement `BaseProviderBuilder`, producing configured Pydantic AI `Model` instances:

- `LocalOpenAIProviderBuilder`: Targets bare-metal K3s `llama-server` (`gemma-4-e2b-it`).
- `OpenRouterProviderBuilder`: Targets the OpenRouter cloud gateway (`google/gemma-4-31b-it`), injecting standard attribution headers (`HTTP-Referer`, `X-Title`).
- `CustomModelProviderBuilder`: Injects mock or test models for hermetic unit testing.

### 2. ModelRouter & Pydantic AI FallbackModel

The `ModelRouter` inspects the active provider configuration:

- When `fallback_provider` is set to `openrouter` (and credentials exist), it constructs:
  `FallbackModel(primary_model, fallback_model, fallback_on=(ModelAPIError,))`
- The `ModelAPIError` condition traps network timeouts, connection drops, and HTTP status codes (`429`, `500`, `502`, `503`, `504`).
- If the primary endpoint fails, Pydantic AI transparently switches inference to the fallback model on the first request attempt without restarting jobs or triggering pipeline crashes.

### 3. Symmetrical Model Toggling

Every application allows operator model flipping using standard environment variables:

- `PRIMARY_LLM_PROVIDER`: Set to `local` (default) or `openrouter`.
- `FALLBACK_LLM_PROVIDER`: Set to `openrouter` (default), `local`, or `none`.

Switching primary inference to the cloud during local maintenance requires toggling a single variable:

```bash
kubectl -n gmail-classifier set env cronjob/gmail-classifier PRIMARY_LLM_PROVIDER=openrouter FALLBACK_LLM_PROVIDER=local
```

---

## Zero-Secret HashiCorp Vault Flow

Secrets are provisioned once in HashiCorp Vault at `kv/openrouter` with field `api_key`.

The External Secrets Operator (ESO) reconciles this secret across all AI namespaces using a shared `ClusterSecretStore`:

- `drive-organizer` $\rightarrow$ `openrouter-credentials`
- `gmail-classifier` $\rightarrow$ `openrouter-credentials`
- `monitoring` $\rightarrow$ `openrouter-credentials`

Each workload mounts `openrouter-credentials` with `optional: true`. If Vault is sealed or the key is not yet present, applications degrade gracefully and run on local SLM without pod initialization failures.
