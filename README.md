# Homelab

A self-hosted bare-metal Kubernetes cluster on Ubuntu 26.04 LTS (node `legion`). It runs K3s `v1.37+` (`v1.37.1+k3s1`). ArgoCD manages 100% of the cluster through GitOps.

- Ansible playbooks install the bare-metal host from scratch with no manual steps
- Tailscale gives secure ingress and Envoy Gateway routes the traffic. Vault and External Secrets keep the credentials
- Local SSD storage uses the K3s Local-Path Provisioner on `/home/k3s-storage`
- The NVIDIA GPU Operator `v26.7.0` gives the NVIDIA GTX 1050 Ti to workloads through the Container Device Interface (CDI)
- The Rancher System Upgrade Controller upgrades K3s automatically with zero downtime
- ArgoCD applies all infrastructure and user applications from this repository through GitOps

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
  - [Core systems map](#core-systems-map)
  - [Platform services map](#platform-services-map)
  - [Network topology](#network-topology)
- [Quick start](#quick-start)
  - [Automated bare metal bring-up](#automated-bare-metal-bring-up)
- [Documentation](#documentation)
- [Repository layout](#repository-layout)
- [Applications](#applications)
- [GitOps model](#gitops-model)
- [Operations](#operations)
- [Maintainers](#maintainers)

## Features

- Single-node / multi-node bare-metal K3s Kubernetes `v1.37.1+k3s1` on node `legion` with Flannel CNI
- Ansible playbooks for host preparation, runtime configuration, and cluster bootstrap
- NVIDIA GPU Operator `v26.7.2` with Container Device Interface (CDI) for GTX 1050 Ti transcoding
- Rancher System Upgrade Controller for declarative K3s upgrades with zero downtime
- ArgoCD ApplicationSets that manage the infrastructure and apps through GitOps
- Tailscale Gateway API ingress with split-horizon DNS
- Vault and External Secrets Operator for central secret management
- Local SSD storage on `/home/k3s-storage` through the Local-Path Provisioner
- Prometheus monitoring stack with Alertmanager and Grafana
- Telegram alerts through @ManassuHomelabBot from Alertmanager, Grafana, and AI assistants
- Media automation stack (Prowlarr, Sonarr, Radarr, Bazarr, Seerr) sharing `jellyfin-media` storage for instant atomic hardlinks
- qBittorrent isolated inside a Gluetun WireGuard VPN sidecar with an iptables firewall killswitch and zero-seeding limits
- Personal finance tracking with Actual Budget and local AI transaction classification
- Local AI inference with Google Gemma 4 (E2B) on the NVIDIA GTX 1050 Ti through llama.cpp
- A Gmail classifier that sorts mail each day with local Gemma 4 and sends Telegram summaries
- A symmetrical Google Drive organizer that classifies documents with local Gemma 4 and syncs with a partner
- Automatic container image updates with ArgoCD Image Updater
- Envoy Gateway data plane for the Kubernetes Gateway API
- Kubescape operator for automatic cluster security scans

## Architecture

### Core systems map

```mermaid
flowchart LR
  subgraph Repo["Homelab Git repo"]
    Ansible["ansible/"]
    Bootstrap["bootstrap/"]
    Infra["infrastructure/"]
    Apps["apps/"]
  end

  subgraph Host["Bare-Metal Host: legion"]
    OS["Ubuntu 26.04 LTS (Kernel 7.0)"]
    GPU["NVIDIA Driver 580 + CDI"]
    Storage["SSD Storage (/home/k3s-storage)"]
    K3s["K3s Server (v1.37.1+k3s1)"]
  end

  subgraph Cluster["Kubernetes Cluster"]
    Argo["ArgoCD + ApplicationSets"]
    Workloads["Infra + Apps"]
  end

  Ansible --> Host
  Host --> K3s
  K3s --> Argo
  Bootstrap --> Argo
  Infra --> Argo
  Apps --> Argo
  Argo --> Workloads
```

### Platform services map

```mermaid
flowchart TB
  subgraph Edge["Edge & Ingress"]
    Tailscale["Tailscale Gateway API"]
    Envoy["Envoy Gateway"]
    DNS["ExternalDNS + Split-Horizon CoreDNS + Tailscale DNS"]
    CertManager["Cert-Manager (Let's Encrypt DNS-01)"]
  end

  subgraph Platform["Platform Services"]
    Vault["Vault"]
    ESO["External Secrets"]
    Storage["Local-Path (/home/k3s-storage)"]
    Metrics["Prometheus + Grafana + Metrics Server"]
    NVIDIA["NVIDIA GPU Operator (CDI)"]
    SUC["System Upgrade Controller"]
    Kubescape["Kubescape Security"]
  end

  subgraph Apps["User Apps"]
    Headlamp["Headlamp"]
    Docs["Docs"]
    Homer["Homer"]
    Media["Media Suite (Jellyfin + *arr + qBittorrent VPN)"]
    HA["Home Assistant"]
    AI["Gemma 4 AI"]
    DNSApp["Technitium DNS"]
    Budget["Actual Budget"]
  end

  Tailscale --> Envoy
  DNS --> Envoy
  CertManager --> Envoy
  Envoy --> Apps
  Vault --> ESO
  ESO --> Apps
  Storage --> Apps
  Metrics --> Apps
  NVIDIA --> Media
  NVIDIA --> AI
  SUC --> Platform
```

### Network topology

```mermaid
flowchart LR
  Public["Public DNS"]
  Tailnet["Tailscale Tailnet"]
  ExternalDNS["ExternalDNS"]
  Gateway["Tailscale Gateway API"]
  Envoy["Envoy Gateway"]
  Routes["HTTPRoutes"]
  Services["Cluster Services"]
  CoreDNS["CoreDNS Rewrite"]

  ExternalDNS --> Public
  Public --> Gateway
  Tailnet --> Gateway
  Gateway --> Envoy
  Envoy --> Routes
  Routes --> Services
  CoreDNS --> Services
```

## Quick start

### Automated bare metal bring-up

Make sure that the target machine `legion` runs Ubuntu and has SSH and sudo access. Then run this command from your workstation:

```bash
./scripts/provision.sh
```

To use the new cluster, run these commands:

```bash
export KUBECONFIG=$PWD/k3s.kubeconfig
kubectl get nodes -o wide
kubectl get pods -A
kubectl get apps -n argocd
```

## Documentation

The full documentation website is at [homelab.sudhanva.me](https://homelab.sudhanva.me). The documentation source files are in `docs/` and use Astro Starlight.

To build the documentation locally, run these commands:

```bash
cd docs
bun install
bun dev
```

Main guides:

- From scratch installation: [Build K3s Cluster from Scratch](docs/src/content/docs/how-to/from-scratch.md)
- Media automation & VPN: [Media Automation and WireGuard VPN Stack](docs/src/content/docs/how-to/media-automation.md)
- Media VPN architecture: [Media VPN and Storage Architecture](docs/src/content/docs/explanation/media-vpn-architecture.md)
- Secrets management: [HashiCorp Vault Secrets Management](docs/src/content/docs/how-to/vault.md)
- Persistent storage: [Local-Path Storage Architecture](docs/src/content/docs/explanation/storage-architecture.md)
- Version matrix: [Component Version Matrix](docs/src/content/docs/reference/versions.md)
- Applications catalog: [Applications Catalog Reference](docs/src/content/docs/reference/applications.md)

## Repository layout

```bash
ansible/          Ansible playbooks, roles, and inventory for bare-metal setup
bootstrap/        ArgoCD bootstrap and ApplicationSet definitions
infrastructure/   Platform components managed by ArgoCD
apps/             User workloads managed by ArgoCD
packages/         Shared monorepo libraries (e.g. homelab-ai)
scripts/          Automation and verification scripts
docs/             Astro Starlight documentation
```

## Applications

| App | Purpose | Hostname |
| --- | --- | --- |
| Docs | Documentation site for cluster guides | `homelab.sudhanva.me` |
| Headlamp | Kubernetes UI with OIDC support and metrics | `headlamp.sudhanva.me` |
| Homer | Home dashboard with service shortcuts | `home.sudhanva.me` |
| Jellyfin | Media streaming with NVIDIA GPU acceleration | `jellyfin.sudhanva.me` |
| Filebrowser | File manager for persistent media volumes | `filebrowser.sudhanva.me` |
| qBittorrent | BitTorrent client isolated behind Gluetun WireGuard VPN | `qbittorrent.sudhanva.me` |
| Prowlarr | Torrent indexer manager and proxy | `prowlarr.sudhanva.me` |
| Sonarr | Television series collection automation | `sonarr.sudhanva.me` |
| Radarr | Movie collection automation | `radarr.sudhanva.me` |
| Bazarr | Automated subtitle download manager | `bazarr.sudhanva.me` |
| Seerr | Media discovery and request interface | `seerr.sudhanva.me` |
| Actual Budget | Privacy-focused personal finance tracking | `actual.sudhanva.me` |
| Technitium DNS | Authoritative and recursive DNS server | `dns.sudhanva.me` |
| Home Assistant | Smart home automation platform | `homeassistant.sudhanva.me` |
| Gemma 4 AI | Local LLM inference on NVIDIA GPU | `ai.sudhanva.me` |
| Gmail Classifier | Symmetrical email sorting and daily summary with a local LLM | Background CronJob |
| Drive Organizer | Symmetrical family document organizer with local Gemma 4 | Background CronJob |
| Actual Classifier | Daily bank transaction categorization with local Gemma 4 | Background CronJob |
| Alert Summarizer | Telegram digest and triage of cluster Prometheus alerts with Gemma 4 | Background CronJob |
| ArgoCD | GitOps control plane UI | `argocd.sudhanva.me` |
| Vault | Central secrets management | `vault.sudhanva.me` |
| Grafana | Metrics dashboards | `grafana.sudhanva.me` |
| Prometheus | Metrics collector and query engine | `prometheus.sudhanva.me` |
| Alertmanager | Alert routing and notifications | `alertmanager.sudhanva.me` |

## GitOps model

ArgoCD uses ApplicationSets to apply all items in `infrastructure/` and `apps/`. After the initial bootstrap, avoid manual `kubectl apply`.

To add an app, do these steps:

- Step 1: Create `apps/<app>/app.yaml`. This file sets the ArgoCD app name, path, and namespace
- Step 2: Add the Kubernetes manifests in the same folder
- Step 3: If you want Image Updater to write overrides, add `kustomization.yaml`

## Operations

To do a routine check of the cluster health, run these commands:

```bash
export KUBECONFIG=$PWD/k3s.kubeconfig
kubectl get nodes -o wide
kubectl get pods -A
kubectl get apps -n argocd
```

Before you push code changes, run this command:

```bash
pre-commit run --all-files
```

## Maintainers

- [Sudhanva Narayana](https://sudhanva.me)
- [Maanasa Narayan](https://maanasanarayan.github.io)
