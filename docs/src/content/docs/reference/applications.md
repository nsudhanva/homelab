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

---

## Media Automation Suite (`media` namespace)

All media automation workloads share the `media` namespace and mount the `jellyfin-media` volume at `/media`.

### Jellyfin

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `media` | Shared media namespace |
| ArgoCD App | `apps/jellyfin/app.yaml` | Application manifest |
| Container Image | `docker.io/jellyfin/jellyfin:12.3` | Video and audio streaming server |
| Internal URL | `http://jellyfin.media.svc:80` | Port 80 targets containerPort 8096 |
| External URL | `https://jellyfin.sudhanva.me` | Tailscale Gateway HTTPS route |
| Storage | `jellyfin-config` (5Gi), `jellyfin-media` (100Gi) | Local-path NVMe partitions |
| Vault Path | `kv/jellyfin/auth` | API keys and administrator credentials |
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
| Vault Path | `kv/qbittorrent/auth`, `kv/qbittorrent/vpn` | Web UI auth and WireGuard keys |
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
| Vault Path | `kv/prowlarr/auth` | API key and administrator login |
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
| Vault Path | `kv/sonarr/auth` | API key and administrator login |
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
| Vault Path | `kv/radarr/auth` | API key and administrator login |
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
| Vault Path | `kv/bazarr/auth` | API key and administrator login |
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
| Vault Path | `kv/seerr/auth` | API key and administrator login |
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
| Vault Path | `kv/filebrowser/auth` | Bcrypt password hash and username |
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
| Vault Path | `kv/headlamp/oidc` | OIDC provider configuration |
| Bitwarden Item | `Homelab - Headlamp GUI Login` | Cluster-admin ServiceAccount token |

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
| DNS Ingress | `100.109.195.34:53` | Tailscale LoadBalancer for UDP and TCP |
| Storage | `technitium-config` (5Gi) | Local-path NVMe partition |
| Vault Path | `kv/technitium/admin` | Web console admin password |
| Bitwarden Item | `Homelab - Technitium DNS Server Admin` | Synchronized administrator login |

### Home Assistant

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `home-assistant` | Dedicated namespace |
| ArgoCD App | `apps/home-assistant/app.yaml` | Application manifest |
| Container Image | `ghcr.io/home-assistant/home-assistant:2026.10.3` | Smart home automation controller |
| External URL | `https://homeassistant.sudhanva.me` | Tailscale Gateway HTTPS route |
| Storage | `home-assistant-config` (5Gi) | Local-path NVMe partition |
| Vault Path | `kv/home-assistant/admin` | Administrator password |
| Bitwarden Item | `Homelab - Home Assistant Admin` | Admin credentials and Muse agent token |

### Actual Budget

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `actual-budget` | Dedicated namespace |
| ArgoCD App | `apps/actual-budget/app.yaml` | Application manifest |
| Container Image | `docker.io/actualbudget/actual-server:26.10.0-alpine` | Personal finance tracking app |
| External URL | `https://actual.sudhanva.me` | Tailscale Gateway HTTPS route |
| Storage | `actual-budget-data` (5Gi) | SQLite database and user files |
| Vault Path | `kv/actual`, `kv/actual-budget/auth`, `kv/actual-budget/simplefin` | Web admin and bank sync tokens |
| Bitwarden Item | `Homelab - Actual Budget Admin` | Synchronized login and sync passwords |

### Documentation Site

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `docs` | Dedicated namespace |
| ArgoCD App | `apps/docs/app.yaml` | Application manifest |
| Container Image | `ghcr.io/nsudhanva/homelab-docs:latest` | Astro Starlight static documentation |
| External URL | `https://homelab.sudhanva.me` | Dual-route (Cloudflare public and Tailscale private) |

---

## AI & Monorepo Microservices

### Llama Server (Gemma 4)

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `llama` | Dedicated namespace |
| ArgoCD App | `apps/llama/app.yaml` | Application manifest |
| Container Image | `ghcr.io/ggml-org/llama.cpp:server-cuda` | Hardware-accelerated local LLM inference |
| External URL | `https://ai.sudhanva.me` | Tailscale Gateway HTTPS route |
| Hardware Resource | `nvidia.com/gpu: 1` | NVIDIA GPU passthrough |
| Storage | `llama-models` (15Gi) | GGUF model files |

### Gmail Classifier

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `gmail-classifier` | Dedicated namespace |
| ArgoCD App | `apps/gmail-classifier/app.yaml` | Application manifest |
| Workload Type | Kubernetes CronJobs | Daily scheduled email triage |
| Vault Path | `kv/gmail/credentials`, `kv/google/accounts/family`, `kv/telegram/bot`, `kv/openrouter` | OAuth and API tokens |
| Bitwarden Items | `Homelab - Google OAuth Personal`, `Homelab - Google OAuth Family` | Synchronized client secrets and refresh tokens |

### Drive Organizer

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `drive-organizer` | Dedicated namespace |
| ArgoCD App | `apps/drive-organizer/app.yaml` | Application manifest |
| Workload Type | Kubernetes CronJobs | Daily scheduled Google Drive organization |
| Vault Path | `kv/gmail/credentials`, `kv/google/accounts/family`, `kv/telegram/bot`, `kv/openrouter` | OAuth and API tokens |

### Actual Classifier

| Property | Value | Notes |
| --- | --- | --- |
| Namespace | `actual-classifier` | Dedicated namespace |
| ArgoCD App | `apps/actual-classifier/app.yaml` | Application manifest |
| Workload Type | Kubernetes CronJobs | Daily scheduled bank transaction classification |
| Vault Path | `kv/actual`, `kv/openrouter` | Actual sync password and OpenRouter key |
