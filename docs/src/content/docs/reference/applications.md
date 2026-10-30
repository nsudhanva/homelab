---
title: Applications Catalog Reference
description: Complete catalog of all user applications deployed by ArgoCD, including ports, manifest paths, Vault secrets, and Bitwarden items.
keywords:
  - kubernetes applications catalog
  - jellyfin kubernetes
  - qbittorrent gluetun
  - prowlarr sonarr radarr bazarr seerr
  - headlamp homer filebrowser
  - home assistant actual budget
  - bitwarden homelab vault
sidebar:
  order: 2
---

# Applications Catalog Reference

This reference lists all workloads running in the homelab cluster.

ArgoCD synchronizes every application automatically through ApplicationSets.

CronJob times are in the `America/Los_Angeles` time zone, which each CronJob declares with `timeZone`.

Vault paths marked "manual" store credentials for humans. No ExternalSecret or manifest in this repository reads them. The Bitwarden items are manual records too, except the two Actual Budget items that `scripts/sync-actual-budget-bw.sh` creates.

---

## Media Automation Suite (`media` namespace)

All media automation workloads share the `media` namespace. The `apps/media` Application owns the namespace (`apps/media/namespace.yaml`, Pod Security Admission `audit` and `warn` at `baseline`). The other media apps only deploy into it.

The `jellyfin-media` volume is shared:

- qBittorrent, Sonarr, Radarr, Bazarr, and Jellyfin mount it at `/media`
- Filebrowser mounts it at `/srv`
- Prowlarr and Seerr do not mount it

### Jellyfin

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `media` | Shared media namespace |
| ArgoCD App | `apps/jellyfin/app.yaml` | Application manifest |
| Container Image | `docker.io/jellyfin/jellyfin:latest` | The base manifest says `12.3`. Argo CD Image Updater overrides it with a digest-pinned `latest` in `apps/jellyfin/.argocd-source-app-jellyfin.yaml` |
| Internal URL | `http://jellyfin.media.svc:80` | Port 80 targets containerPort 8096 |
| External URL | `https://jellyfin.sudhanva.me` | Tailscale Gateway HTTPS route |
| Storage | `jellyfin-config` (5Gi), `jellyfin-media` (100Gi) | Local-path NVMe partitions |
| Vault Path | `kv/jellyfin/auth` | Manual. API keys and administrator credentials |
| Bitwarden Item | `Homelab - Jellyfin Admin` | Synchronized administrator login |

### qBittorrent + Gluetun VPN

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `media` | Shared media namespace |
| ArgoCD App | `apps/qbittorrent/app.yaml` | Application manifest |
| Container Images | `ghcr.io/qdm12/gluetun:v3.41.3`, `lscr.io/linuxserver/qbittorrent:5.3.0` | Sidecar VPN and torrent client |
| Internal URL | `http://qbittorrent.media.svc:80` | Port 80 targets containerPort 8080 |
| External URL | `https://qbittorrent.sudhanva.me` | Tailscale Gateway HTTPS route |
| Storage | `qbittorrent-config` (1Gi), `jellyfin-media` (100Gi) | Local-path NVMe partitions |
| Vault Path | `kv/qbittorrent/vpn`, `kv/qbittorrent/auth` | `kv/qbittorrent/vpn` feeds the `qbittorrent-vpn` ExternalSecret (WireGuard keys). `kv/qbittorrent/auth` is manual (Web UI login) |
| Bitwarden Items | `Homelab - qBittorrent Admin`, `Homelab - qBittorrent WireGuard VPN` | Synchronized credentials |

### Prowlarr

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `media` | Shared media namespace |
| ArgoCD App | `apps/prowlarr/app.yaml` | Application manifest |
| Container Image | `lscr.io/linuxserver/prowlarr:2.6.5.5623-ls165` | Torrent indexer manager |
| Internal URL | `http://prowlarr.media.svc:80` | Port 80 targets containerPort 9696 |
| External URL | `https://prowlarr.sudhanva.me` | Tailscale Gateway HTTPS route |
| Storage | `prowlarr-config` (1Gi) | Local-path NVMe partition |
| Vault Path | `kv/prowlarr/auth` | Manual. API key and administrator login |
| Bitwarden Item | `Homelab - Prowlarr Admin` | Synchronized administrator login |

### Sonarr

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `media` | Shared media namespace |
| ArgoCD App | `apps/sonarr/app.yaml` | Application manifest |
| Container Image | `lscr.io/linuxserver/sonarr:4.0.20.3014-ls1` | Television series collection manager |
| Internal URL | `http://sonarr.media.svc:80` | Port 80 targets containerPort 8989 |
| External URL | `https://sonarr.sudhanva.me` | Tailscale Gateway HTTPS route |
| Storage | `sonarr-config` (1Gi), `jellyfin-media` (100Gi) | Local-path NVMe partitions |
| Vault Path | `kv/sonarr/auth` | Manual. API key and administrator login |
| Bitwarden Item | `Homelab - Sonarr Admin` | Synchronized administrator login |

### Radarr

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `media` | Shared media namespace |
| ArgoCD App | `apps/radarr/app.yaml` | Application manifest |
| Container Image | `lscr.io/linuxserver/radarr:6.4.4.10685-ls323` | Movie collection manager |
| Internal URL | `http://radarr.media.svc:80` | Port 80 targets containerPort 7878 |
| External URL | `https://radarr.sudhanva.me` | Tailscale Gateway HTTPS route |
| Storage | `radarr-config` (1Gi), `jellyfin-media` (100Gi) | Local-path NVMe partitions |
| Vault Path | `kv/radarr/auth` | Manual. API key and administrator login |
| Bitwarden Item | `Homelab - Radarr Admin` | Synchronized administrator login |

### Bazarr

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `media` | Shared media namespace |
| ArgoCD App | `apps/bazarr/app.yaml` | Application manifest |
| Container Image | `lscr.io/linuxserver/bazarr:v1.6.2-ls369` | Automated subtitle downloader |
| Internal URL | `http://bazarr.media.svc:80` | Port 80 targets containerPort 6767 |
| External URL | `https://bazarr.sudhanva.me` | Tailscale Gateway HTTPS route |
| Storage | `bazarr-config` (1Gi), `jellyfin-media` (100Gi) | Local-path NVMe partitions |
| Vault Path | `kv/bazarr/auth` | Manual. API key and administrator login |
| Bitwarden Item | `Homelab - Bazarr Admin` | Synchronized administrator login |

### Seerr

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `media` | Shared media namespace |
| ArgoCD App | `apps/seerr/app.yaml` | Application manifest |
| Container Image | `ghcr.io/seerr-team/seerr:v3.5.1` | Media request discovery interface |
| Internal URL | `http://seerr.media.svc:80` | Port 80 targets containerPort 5055 |
| External URL | `https://seerr.sudhanva.me` | Tailscale Gateway HTTPS route |
| Storage | `seerr-config` (1Gi) | Local-path NVMe partition |
| Vault Path | `kv/seerr/auth` | Manual. API key and administrator login |
| Bitwarden Item | `Homelab - Seerr Admin` | Synchronized administrator login |

### Filebrowser

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `media` | Shared media namespace |
| ArgoCD App | `apps/filebrowser/app.yaml` | Application manifest |
| Container Image | `docker.io/filebrowser/filebrowser:v2.63.23` | Web file management interface |
| Internal URL | `http://filebrowser.media.svc:80` | Port 80 targets containerPort 8080 |
| External URL | `https://filebrowser.sudhanva.me` | Tailscale Gateway HTTPS route |
| Storage | `filebrowser-config` (1Gi), `jellyfin-media` (100Gi) | Local-path NVMe partitions |
| Vault Path | `kv/filebrowser/auth` | `username` and `password_hash` (bcrypt), read by the `filebrowser-auth` ExternalSecret |
| Bitwarden Item | `Homelab - Filebrowser Admin` | Synchronized administrator login |

---

## Core Homelab Services

### Headlamp

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `headlamp` | Dedicated namespace |
| ArgoCD App | `apps/headlamp/app.yaml` | Application manifest |
| Container Image | `ghcr.io/headlamp-k8s/headlamp:v0.46.0` | Kubernetes cluster dashboard |
| External URL | `https://headlamp.sudhanva.me` | Tailscale Gateway HTTPS route |
| Authentication | `headlamp-token` Secret | ServiceAccount token for the `headlamp` ServiceAccount (bound to `cluster-admin`). Headlamp runs with `-in-cluster -unsafe-use-service-account-token`. No Vault path and no OIDC |
| Bitwarden Item | `Homelab - Headlamp GUI Login` | Copy of the ServiceAccount token |

### Homer Dashboard

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `homer` | Dedicated namespace |
| ArgoCD App | `apps/homer/app.yaml` | Application manifest |
| Container Image | `b4bz/homer:v26.08.3` | Personal service launch dashboard |
| External URL | `https://home.sudhanva.me` | Tailscale Gateway HTTPS route |
| ConfigMap | `apps/homer/configmap.yaml` | Declarative dashboard links |

### Technitium DNS Server

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `technitium` | Dedicated namespace |
| ArgoCD App | `apps/technitium/app.yaml` | Application manifest |
| Container Image | `technitium/dns-server:15.6.2` | Recursive ad-blocking DNS server |
| External URL | `https://dns.sudhanva.me` | Tailscale Gateway HTTPS route |
| DNS Ingress | `technitium-dns:53` | Tailscale LoadBalancer Service `technitium-tailscale` for UDP and TCP. Find its tailnet IP in the Tailscale admin console |
| Storage | `technitium-config` (5Gi) | Local-path NVMe partition |
| Vault Path | `kv/technitium/admin` | `admin-user` and `admin-password`, read by the `technitium-admin` ExternalSecret |
| Bitwarden Item | `Homelab - Technitium DNS Server Admin` | Synchronized administrator login |

### Home Assistant

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `home-assistant` | Dedicated namespace |
| ArgoCD App | `apps/home-assistant/app.yaml` | Application manifest |
| Container Image | `ghcr.io/home-assistant/home-assistant:2026.10.3` | Smart home automation controller |
| External URL | `https://homeassistant.sudhanva.me` | Tailscale Gateway HTTPS route |
| Storage | `home-assistant-config` (5Gi) | Local-path NVMe partition |
| Vault Path | `kv/home-assistant/admin` | Manual. Administrator password |
| Bitwarden Item | `Homelab - Home Assistant Admin` | Admin credentials and Muse agent token |

### Actual Budget

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `actual-budget` | Dedicated namespace |
| ArgoCD App | `apps/actual-budget/app.yaml` | Application manifest |
| Container Image | `docker.io/actualbudget/actual-server:26.10.0-alpine` | Personal finance tracking app |
| External URL | `https://actual.sudhanva.me` | Tailscale Gateway HTTPS route |
| Storage | `actual-budget-data` (5Gi) | SQLite database and user files |
| Vault Path | `kv/actual`, `kv/actual-budget/simplefin` | `kv/actual` (`password`) is read by the `actual-classifier-secrets` ExternalSecret and by the Bitwarden sync script. `kv/actual-budget/simplefin` (`setup_token`) is read only by the script. `kv/actual-budget/auth` is not used |
| Bitwarden Items | `Actual Budget (Homelab)`, `SimpleFIN Bridge Setup Token (Actual Budget)` | Created by `scripts/sync-actual-budget-bw.sh` |

### Documentation Site

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `docs` | Dedicated namespace |
| ArgoCD App | `apps/docs/app.yaml` | Application manifest |
| Container Image | `ghcr.io/nsudhanva/homelab-docs:latest` | Astro Starlight static documentation. Argo CD Image Updater pins the digest |
| Internal URL | `http://docs.docs.svc:80` | The container listens on port 80 |
| External URLs | `https://homelab.sudhanva.me`, `https://docs.sudhanva.me` | One HTTPRoute on the Tailscale gateway |
| Cloudflare Pages | `docs/wrangler.toml` | Pages config with `pages_build_output_dir = "dist"`. No workflow in this repository deploys it |

---

## AI & Monorepo Microservices

### Llama Server (Gemma 4)

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `llama` | Dedicated namespace |
| ArgoCD App | `apps/llama/app.yaml` | Application manifest |
| Container Images | `ghcr.io/ggml-org/llama.cpp:server-cuda`, `curlimages/curl:8.23.0` | Local LLM inference, and the `download-model` init container |
| Internal URL | `http://llama-server.llama.svc.cluster.local:8080/v1` | `LOCAL_LLM_BASE_URL`, the last fallback of the `homelab-ai` chain |
| External URL | `https://ai.sudhanva.me` | Tailscale Gateway HTTPS route |
| Hardware Resource | `nvidia.com/gpu: 1` | NVIDIA GPU passthrough |
| Storage | `llama-models` (15Gi) | GGUF model files |

### Gmail Classifier

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `gmail-classifier` | Dedicated namespace |
| ArgoCD App | `apps/gmail-classifier/app.yaml` | Application manifest |
| Container Image | `ghcr.io/nsudhanva/homelab-gmail-classifier:latest` | Built by CI |
| Workload Type | Kubernetes CronJobs | Per account: daily triage (`gmail-classifier-personal` 01:00, `gmail-classifier-family` 01:15) and weekly mark-as-read (`gmail-mark-read-personal` Sunday 04:00, `gmail-mark-read-family` Sunday 04:15) |
| Vault Path | `kv/gmail/credentials`, `kv/google/accounts/family`, `kv/telegram/bot`, `kv/anthropic`, `kv/openrouter` | Google OAuth per account, Telegram bot token, and model API keys (`kv/anthropic`: `api_key`, `workspace_id`; `kv/openrouter`: `api_key`) through `homelab-ai-credentials` |
| Bitwarden Items | `Homelab - Google OAuth Personal`, `Homelab - Google OAuth Family` | Synchronized client secrets and refresh tokens |

### Drive Organizer

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `drive-organizer` | Dedicated namespace |
| ArgoCD App | `apps/drive-organizer/app.yaml` | Application manifest |
| Container Image | `ghcr.io/nsudhanva/homelab-drive-organizer:latest` | Built by CI |
| Workload Type | Kubernetes CronJobs | Daily per account: `drive-organizer-personal` 02:00, `drive-organizer-family` 02:15 |
| Vault Path | `kv/gmail/credentials`, `kv/google/accounts/family`, `kv/telegram/bot`, `kv/anthropic`, `kv/openrouter` | Google OAuth per account (`drive-credentials-<nickname>`), Telegram bot token, and model API keys through `homelab-ai-credentials` |

### Actual Classifier

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `actual-classifier` | Dedicated namespace |
| ArgoCD App | `apps/actual-classifier/app.yaml` | Application manifest |
| Container Image | `ghcr.io/nsudhanva/homelab-actual-classifier:latest` | Built by CI |
| Workload Type | Kubernetes CronJob | `actual-classifier`, daily at 03:00 |
| Vault Path | `kv/actual`, `kv/anthropic`, `kv/openrouter` | Actual server password, and model API keys through `homelab-ai-credentials` |

### Alert Summarizer

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `monitoring` | Shares the namespace of the Prometheus stack |
| ArgoCD App | `apps/alert-summarizer/app.yaml` | Application manifest |
| Container Image | `ghcr.io/nsudhanva/homelab-alert-summarizer:latest` | Built by CI. Argo CD Image Updater pins the digest |
| Workload Type | Deployment | Alertmanager webhook receiver |
| Internal URL | `http://alert-summarizer.monitoring.svc.cluster.local:8000/webhook` | Service port 8000. No HTTPRoute |
| Configuration | `homelab-ai` ConfigMap, `homelab-ai-credentials` Secret | Shared model chain and API keys |
| Vault Path | `kv/telegram/bot`, `kv/anthropic`, `kv/openrouter` | The bot token reaches the pod through the `alertmanager-telegram` Secret, mounted at `/etc/secrets` |
