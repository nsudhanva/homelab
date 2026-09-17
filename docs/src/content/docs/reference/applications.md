---
title: Applications Catalog Reference
description: Reference catalog of all user applications deployed via ArgoCD including Jellyfin, Filebrowser, Headlamp, Home Assistant, Homer dashboard, and documentation site with their manifest paths.
keywords:
  - kubernetes applications
  - jellyfin kubernetes
  - headlamp deployment
  - homer dashboard
  - filebrowser kubernetes
  - home assistant kubernetes
  - kubernetes app manifests
  - argocd apps
sidebar:
  order: 2
---

# Applications Catalog

This page lists the applications already defined in `apps/`.

## Media namespace

The `media` namespace is shared by Jellyfin and Filebrowser so they can use the same PVCs.

- Namespace definition: `apps/media/namespace.yaml`
- ArgoCD app: `apps/media/app.yaml`

## Jellyfin

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/media/namespace.yaml` | Shared `media` namespace |
| App config | `apps/jellyfin/app.yaml` | ArgoCD app definition |
| Deployment | `apps/jellyfin/deployment.yaml` | Requests NVIDIA GPUs by default (`nvidia.com/gpu`) |
| Service | `apps/jellyfin/service.yaml` | ClusterIP on port 80 |
| HTTPRoute | `apps/jellyfin/httproute.yaml` | `jellyfin.sudhanva.me` |
| PVCs | `apps/jellyfin/pvc-config.yaml` and `apps/jellyfin/pvc-media.yaml` | Local-path SSD storage |

## Filebrowser

| Item | Path | Notes |
| --- | --- | --- |
| App config | `apps/filebrowser/app.yaml` | ArgoCD app definition |
| Deployment | `apps/filebrowser/deployment.yaml` | Auth via Vault-backed secret, mounts Jellyfin media |
| Service | `apps/filebrowser/service.yaml` | ClusterIP on port 80 |
| HTTPRoute | `apps/filebrowser/httproute.yaml` | `filebrowser.sudhanva.me` |

## Docs site

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/docs/namespace.yaml` | Dedicated `docs` namespace |
| App config | `apps/docs/app.yaml` | ArgoCD app definition |
| Deployment | `apps/docs/deployment.yaml` | Uses `ghcr.io/nsudhanva/homelab-docs:latest` |
| Service | `apps/docs/service.yaml` | ClusterIP on port 80 |
| HTTPRoute | `apps/docs/httproute.yaml` | `docs.sudhanva.me` split-horizon (public Pages + tailnet Gateway) |

## Headlamp

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/headlamp/namespace.yaml` | Dedicated `headlamp` namespace |
| App config | `apps/headlamp/app.yaml` | ArgoCD app definition |
| ServiceAccount | `apps/headlamp/serviceaccount.yaml` | Headlamp dashboard service account |
| ClusterRoleBinding | `apps/headlamp/clusterrolebinding.yaml` | Grants `cluster-admin` privileges to service account |
| Secret | `apps/headlamp/secret-token.yaml` | Permanent token secret for seamless in-cluster login |
| Deployment | `apps/headlamp/deployment.yaml` | `ghcr.io/headlamp-k8s/headlamp:v0.45.0` with `-unsafe-use-service-account-token` |
| Service | `apps/headlamp/service.yaml` | ClusterIP on port 80 |
| HTTPRoute | `apps/headlamp/httproute.yaml` | `headlamp.sudhanva.me` |
| ServiceMonitor | `apps/headlamp/servicemonitor.yaml` | Prometheus scrape config |

## Home dashboard (Homer)

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/homer/namespace.yaml` | Dedicated `homer` namespace |
| App config | `apps/homer/app.yaml` | ArgoCD app definition |
| ConfigMap | `apps/homer/configmap.yaml` | Homer `config.yml` |
| Deployment | `apps/homer/deployment.yaml` | Uses `b4bz/homer:v26.08.3` |
| Service | `apps/homer/service.yaml` | ClusterIP on port 80 |
| HTTPRoute | `apps/homer/httproute.yaml` | `home.sudhanva.me` |

## Technitium DNS Server

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/technitium/namespace.yaml` | Dedicated `technitium` namespace |
| App config | `apps/technitium/app.yaml` | ArgoCD app definition |
| Deployment | `apps/technitium/deployment.yaml` | `technitium/dns-server:latest` |
| Service | `apps/technitium/service.yaml` | ClusterIP on port 5380 (HTTP) and 53 (DNS) |
| Tailscale LB | `apps/technitium/service-tailscale.yaml` | Tailscale LoadBalancer on port 53 |
| HTTPRoute | `apps/technitium/httproute.yaml` | `dns.sudhanva.me` |
| PVC | `apps/technitium/pvc.yaml` | 5Gi local-path storage for `/etc/dns` |
| ExternalSecret | `apps/technitium/external-secret.yaml` | Vault integration for admin API credentials |
| ConfigMap | `apps/technitium/configmap-settings.yaml` | Declarative settings for blocklists, forwarders, DNSSEC |
| PostSync Job | `apps/technitium/job-sync.yaml` | GitOps configuration sync via Technitium REST API |

## Home Assistant

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/home-assistant/namespace.yaml` | Dedicated `home-assistant` namespace |
| App config | `apps/home-assistant/app.yaml` | ArgoCD app definition |
| ConfigMap (Core) | `apps/home-assistant/configmap-core.yaml` | Declarative `configuration.yaml` with reverse proxy trusted proxies |
| ConfigMap (Packages) | `apps/home-assistant/configmap-packages.yaml` | Declarative packages for Google Cast, Sony TV, PS5, Xfinity |
| Deployment | `apps/home-assistant/deployment.yaml` | `ghcr.io/home-assistant/home-assistant:2026.9.2` |
| Service | `apps/home-assistant/service.yaml` | ClusterIP on port 8123 |
| HTTPRoute | `apps/home-assistant/httproute.yaml` | `homeassistant.sudhanva.me` via tailnet gateway |
| PVC | `apps/home-assistant/pvc.yaml` | 5Gi local-path storage for `/config` |

## Llama Server (Gemma 4)

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/llama/namespace.yaml` | Dedicated `llama` namespace |
| App config | `apps/llama/app.yaml` | ArgoCD app definition |
| Deployment | `apps/llama/deployment.yaml` | `ghcr.io/ggml-org/llama.cpp:server-cuda` with Gemma 4 E2B |
| Service | `apps/llama/service.yaml` | ClusterIP on port 8080 |
| HTTPRoute | `apps/llama/httproute.yaml` | `ai.sudhanva.me` via tailnet gateway |
| PVC | `apps/llama/pvc.yaml` | 15Gi local-path storage for `/models` |

## Gmail Classifier

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/gmail-classifier/namespace.yaml` | Dedicated `gmail-classifier` namespace |
| App config | `apps/gmail-classifier/app.yaml` | ArgoCD app definition |
| CronJob | `apps/gmail-classifier/cronjob.yaml` | Daily schedule at `0 1 * * *` invoking `uv run gmail-classifier` |
| ExternalSecret | `apps/gmail-classifier/secret.yaml` | Vault integration for Google OAuth client credentials and refresh token |
| Python App | `apps/gmail-classifier/src/gmail_classifier/` | Automated Gmail triage engine using local Gemma 4 and Telegram alerts |
