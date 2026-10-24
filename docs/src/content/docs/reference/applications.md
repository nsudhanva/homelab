---
title: Applications Catalog Reference
description: Catalog of the user applications that ArgoCD deploys, with their manifest paths. It includes Jellyfin, Filebrowser, Headlamp, Home Assistant, Homer, and the docs site.
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

This page lists the applications in `apps/`.

## Media namespace

Jellyfin, Seerr, Radarr, Sonarr, Bazarr, Prowlarr, qBittorrent, and Filebrowser use the same `media` namespace. Thus, they can share the `jellyfin-media` PVC for zero-copy hardlinks and immediate library updates.

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

## qBittorrent + Gluetun VPN

| Item | Path | Notes |
| --- | --- | --- |
| App config | `apps/qbittorrent/app.yaml` | ArgoCD app definition |
| ExternalSecret | `apps/qbittorrent/external-secret-vpn.yaml` | Syncs WireGuard credentials from Vault `kv/qbittorrent/vpn` |
| Deployment | `apps/qbittorrent/deployment.yaml` | `ghcr.io/qdm12/gluetun:v3.41.3` + `lscr.io/linuxserver/qbittorrent:5.3.0`, mounts `jellyfin-media` |
| Service | `apps/qbittorrent/service.yaml` | ClusterIP on port 80 (targetPort 8080) |
| HTTPRoute | `apps/qbittorrent/httproute.yaml` | `qbittorrent.sudhanva.me` |
| PVC | `apps/qbittorrent/pvc-config.yaml` | 1Gi local-path storage for `/config` |

## Prowlarr

| Item | Path | Notes |
| --- | --- | --- |
| App config | `apps/prowlarr/app.yaml` | ArgoCD app definition |
| Deployment | `apps/prowlarr/deployment.yaml` | `lscr.io/linuxserver/prowlarr:2.6.5.5623-ls165` |
| Service | `apps/prowlarr/service.yaml` | ClusterIP on port 80 (targetPort 9696) |
| HTTPRoute | `apps/prowlarr/httproute.yaml` | `prowlarr.sudhanva.me` |
| PVC | `apps/prowlarr/pvc-config.yaml` | 1Gi local-path storage for `/config` |

## Sonarr

| Item | Path | Notes |
| --- | --- | --- |
| App config | `apps/sonarr/app.yaml` | ArgoCD app definition |
| Deployment | `apps/sonarr/deployment.yaml` | `lscr.io/linuxserver/sonarr:4.0.20.3014-ls1`, mounts `jellyfin-media` |
| Service | `apps/sonarr/service.yaml` | ClusterIP on port 80 (targetPort 8989) |
| HTTPRoute | `apps/sonarr/httproute.yaml` | `sonarr.sudhanva.me` |
| PVC | `apps/sonarr/pvc-config.yaml` | 1Gi local-path storage for `/config` |

## Radarr

| Item | Path | Notes |
| --- | --- | --- |
| App config | `apps/radarr/app.yaml` | ArgoCD app definition |
| Deployment | `apps/radarr/deployment.yaml` | `lscr.io/linuxserver/radarr:6.4.4.10685-ls323`, mounts `jellyfin-media` |
| Service | `apps/radarr/service.yaml` | ClusterIP on port 80 (targetPort 7878) |
| HTTPRoute | `apps/radarr/httproute.yaml` | `radarr.sudhanva.me` |
| PVC | `apps/radarr/pvc-config.yaml` | 1Gi local-path storage for `/config` |

## Bazarr

| Item | Path | Notes |
| --- | --- | --- |
| App config | `apps/bazarr/app.yaml` | ArgoCD app definition |
| Deployment | `apps/bazarr/deployment.yaml` | `lscr.io/linuxserver/bazarr:v1.6.2-ls369`, mounts `jellyfin-media` |
| Service | `apps/bazarr/service.yaml` | ClusterIP on port 80 (targetPort 6767) |
| HTTPRoute | `apps/bazarr/httproute.yaml` | `bazarr.sudhanva.me` |
| PVC | `apps/bazarr/pvc-config.yaml` | 1Gi local-path storage for `/config` |

## Seerr

| Item | Path | Notes |
| --- | --- | --- |
| App config | `apps/seerr/app.yaml` | ArgoCD app definition |
| Deployment | `apps/seerr/deployment.yaml` | `ghcr.io/seerr-team/seerr:v3.5.1` |
| Service | `apps/seerr/service.yaml` | ClusterIP on port 80 (targetPort 5055) |
| HTTPRoute | `apps/seerr/httproute.yaml` | `seerr.sudhanva.me` |
| PVC | `apps/seerr/pvc-config.yaml` | 1Gi local-path storage for `/app/config` |

## Filebrowser

| Item | Path | Notes |
| --- | --- | --- |
| App config | `apps/filebrowser/app.yaml` | ArgoCD app definition |
| Deployment | `apps/filebrowser/deployment.yaml` | Auth through a Vault-backed secret, mounts Jellyfin media |
| Service | `apps/filebrowser/service.yaml` | ClusterIP on port 80 |
| HTTPRoute | `apps/filebrowser/httproute.yaml` | `filebrowser.sudhanva.me` |

## Docs site

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/docs/namespace.yaml` | Dedicated `docs` namespace |
| App config | `apps/docs/app.yaml` | ArgoCD app definition |
| Deployment | `apps/docs/deployment.yaml` | Uses `ghcr.io/nsudhanva/homelab-docs:latest` |
| Service | `apps/docs/service.yaml` | ClusterIP on port 80 |
| HTTPRoute | `apps/docs/httproute.yaml` | `homelab.sudhanva.me` split-horizon (public Cloudflare + tailnet Gateway) |

## Headlamp

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/headlamp/namespace.yaml` | Dedicated `headlamp` namespace |
| App config | `apps/headlamp/app.yaml` | ArgoCD app definition |
| ServiceAccount | `apps/headlamp/serviceaccount.yaml` | Headlamp dashboard service account |
| ClusterRoleBinding | `apps/headlamp/clusterrolebinding.yaml` | Gives `cluster-admin` privileges to the service account |
| Secret | `apps/headlamp/secret-token.yaml` | Permanent token secret for in-cluster login |
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
| PostSync Job | `apps/technitium/job-sync.yaml` | GitOps configuration sync through the Technitium REST API |

## Home Assistant

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/home-assistant/namespace.yaml` | Dedicated `home-assistant` namespace |
| App config | `apps/home-assistant/app.yaml` | ArgoCD app definition |
| ConfigMap (Core) | `apps/home-assistant/configmap-core.yaml` | Declarative `configuration.yaml` with reverse proxy trusted proxies |
| ConfigMap (Packages) | `apps/home-assistant/configmap-packages.yaml` | Declarative packages for Google Cast, Sony TV, PS5, Xfinity |
| Deployment | `apps/home-assistant/deployment.yaml` | `ghcr.io/home-assistant/home-assistant:2026.9.2` |
| Service | `apps/home-assistant/service.yaml` | ClusterIP on port 8123 |
| HTTPRoute | `apps/home-assistant/httproute.yaml` | `homeassistant.sudhanva.me` through the tailnet gateway |
| PVC | `apps/home-assistant/pvc.yaml` | 5Gi local-path storage for `/config` |

## Llama Server (Gemma 4)

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/llama/namespace.yaml` | Dedicated `llama` namespace |
| App config | `apps/llama/app.yaml` | ArgoCD app definition |
| Deployment | `apps/llama/deployment.yaml` | `ghcr.io/ggml-org/llama.cpp:server-cuda` with Gemma 4 E2B |
| Service | `apps/llama/service.yaml` | ClusterIP on port 8080 |
| HTTPRoute | `apps/llama/httproute.yaml` | `ai.sudhanva.me` through the tailnet gateway |
| PVC | `apps/llama/pvc.yaml` | 15Gi local-path storage for `/models` |

## Gmail Classifier

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/gmail-classifier/namespace.yaml` | Dedicated `gmail-classifier` namespace |
| App config | `apps/gmail-classifier/app.yaml` | ArgoCD app definition |
| CronJob | `apps/gmail-classifier/cronjob-<nickname>.yaml` | Daily classification per account, generated from `apps/accounts.yaml` |
| CronJob | `apps/gmail-classifier/cronjob-<nickname>-mark-read.yaml` | Weekly `--mark-all-read` per account (Sundays) |
| ExternalSecret | `apps/gmail-classifier/secret.yaml` | Vault integration for Google OAuth client credentials and refresh token |
| Python App | `apps/gmail-classifier/src/gmail_classifier/` | Gmail triage engine that uses local Gemma 4 and sends Telegram alerts |

## Drive Organizer

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/drive-organizer/namespace.yaml` | Dedicated `drive-organizer` namespace |
| App config | `apps/drive-organizer/app.yaml` | ArgoCD app definition |
| CronJob | `apps/drive-organizer/cronjob.yaml` | Daily schedule at `0 2 * * *` that runs `uv run drive-organizer` |
| ExternalSecret | `apps/drive-organizer/secret.yaml` | Vault integration for Google OAuth credentials and Telegram bot token |
| Python App | `apps/drive-organizer/src/drive_organizer/` | Symmetrical Google Drive organizer for personal and family accounts, uses local Gemma 4 |

## Actual Budget

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/actual-budget/namespace.yaml` | Dedicated `actual-budget` namespace |
| App config | `apps/actual-budget/app.yaml` | ArgoCD app definition |
| Deployment | `apps/actual-budget/deployment.yaml` | `docker.io/actualbudget/actual-server:26.9.0-alpine` |
| Service | `apps/actual-budget/service.yaml` | ClusterIP on port 5006 |
| HTTPRoute | `apps/actual-budget/httproute.yaml` | `actual.sudhanva.me` through the tailnet gateway |
| PVC | `apps/actual-budget/pvc.yaml` | 5Gi local-path storage for `/data` (SQLite database and user files) |

## Actual Classifier

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/actual-classifier/namespace.yaml` | Dedicated `actual-classifier` namespace |
| App config | `apps/actual-classifier/app.yaml` | ArgoCD app definition |
| CronJob | `apps/actual-classifier/cronjob.yaml` | Scheduled daily at 03:00 (`0 3 * * *`), after Gmail and Drive jobs |
| ExternalSecret | `apps/actual-classifier/secret.yaml` | Vault integration for Actual Budget and OpenRouter credentials |
| Python App | `apps/actual-classifier/src/actual_classifier/` | Puts transactions into categories and adds tags with local Gemma 4 |
