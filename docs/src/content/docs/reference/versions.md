---
title: Component Version Matrix
description: Pinned versions of all components, such as K3s, ArgoCD, Envoy Gateway, and Vault, with the location of each configuration file.
keywords:
  - k3s version
  - kubernetes version
  - argocd version
  - envoy gateway version
  - helm chart versions
  - kubernetes component versions
sidebar:
  order: 3
---

# Version Matrix

When you upgrade components, keep these versions aligned.

:::note

Check the latest stable release before changing any pinned version.

:::

- K3s: `v1.37.1+k3s1` in `ansible/group_vars/all.yaml`
- Kubernetes: `v1.37.1` from K3s
- kubeconform: `v0.7.0` in `scripts/run-kubeconform.sh` (validates against Kubernetes `1.37.0`)
- containerd: bundled with K3s (not pinned in the repo; `kubectl get nodes -o wide` shows the running version)
- Host OS: Ubuntu 26.04 LTS (the point release is not pinned in the repo; `kubectl get nodes -o wide` shows it)
- CNI: Flannel (K3s built-in)
- Storage: Local-Path Provisioner (data path `/home/k3s-storage`)
- ArgoCD: `v3.5.6` in `bootstrap/argocd/kustomization.yaml`
- ArgoCD Image Updater chart: `1.3.2` in `infrastructure/argocd-image-updater/argocd-image-updater.yaml`
- Tailscale Operator: `1.104.2` in `infrastructure/tailscale/tailscale-operator.yaml`
- Envoy Gateway: `v1.9.2` chart and `docker.io/envoyproxy/gateway:v1.9.2` controller image in `infrastructure/envoy-gateway/envoy-gateway.yaml` (the chart's bundled CRDs are off)
- Kubescape Operator chart: `1.40.5` in `infrastructure/kubescape/kubescape.yaml`
- Gateway API CRDs: `v1.6.3` in `infrastructure/gateway-api-crds/gateway-api-crds.yaml`
- Envoy Gateway CRDs: `v1.9.2` in `infrastructure/envoy-gateway-crds/`
- cert-manager: `v1.21.3` in `infrastructure/cert-manager/cert-manager.yaml`
- ExternalDNS chart: `1.23.0` in `infrastructure/external-dns/external-dns.yaml`
- External Secrets CRDs: `v2.14.0` in `infrastructure/external-secrets-crds/`
- External Secrets chart: `2.14.0` in `infrastructure/external-secrets/external-secrets.yaml`
- kube-prometheus-stack chart: `92.11.0` in `infrastructure/prometheus/prometheus.yaml`
- Prometheus Operator CRDs chart: `32.0.2` in `infrastructure/prometheus-operator-crds/prometheus-operator-crds.yaml`
- Metrics Server chart: `3.14.0` in `infrastructure/metrics-server/metrics-server.yaml`
- Vault chart: `0.34.1` in `infrastructure/vault/vault.yaml`
- NVIDIA GPU Operator: `v26.7.2` in `infrastructure/gpu/gpu-operator.yaml`
- System Upgrade Controller: `v0.20.2` release manifests in `infrastructure/system-upgrade-controller/kustomization.yaml`
- System Upgrade Controller kubectl Job image: `rancher/kubectl:v1.36.2` in `infrastructure/system-upgrade-controller/kustomization.yaml`
- K3s upgrade Plan target: `v1.37.1+k3s1` in `infrastructure/system-upgrade-controller/k3s-upgrade-plan.yaml`
- CoreDNS: `1.15.0` in `infrastructure/tailscale-dns/deployment.yaml`
- tailscale-dns updater: `alpine:3.24.3` in `infrastructure/tailscale-dns/cronjob-updater.yaml`, which downloads kubectl `v1.37.1` at run time
- curl helper: `curlimages/curl:8.23.0` in `apps/llama/deployment.yaml` (init container `download-model`) and `apps/technitium/job-sync.yaml`
- Homer: `v26.08.3` in `apps/homer/deployment.yaml`
- Headlamp: `v0.46.0` in `apps/headlamp/deployment.yaml`
- Technitium DNS Server: `15.6.2` in `apps/technitium/deployment.yaml`
- Home Assistant: `2026.10.3` in `apps/home-assistant/deployment.yaml`
- llama.cpp (Gemma 4): `server-cuda` in `apps/llama/deployment.yaml`
- Jellyfin: `latest`, pinned by digest in `apps/jellyfin/.argocd-source-app-jellyfin.yaml` (Image Updater). The base manifest `apps/jellyfin/deployment.yaml` says `12.3`, but the override replaces it
- Gluetun: `v3.41.3` in `apps/qbittorrent/deployment.yaml`
- qBittorrent: `5.3.0` in `apps/qbittorrent/deployment.yaml`
- Prowlarr: `2.6.5.5623-ls165` in `apps/prowlarr/deployment.yaml`
- Sonarr: `4.0.20.3014-ls1` in `apps/sonarr/deployment.yaml`
- Radarr: `6.4.4.10685-ls323` in `apps/radarr/deployment.yaml`
- Bazarr: `v1.6.2-ls369` in `apps/bazarr/deployment.yaml`
- Seerr: `v3.5.1` in `apps/seerr/deployment.yaml`
- Filebrowser: `v2.63.23` in `apps/filebrowser/deployment.yaml`
- Alertmanager and Prometheus: the versions that kube-prometheus-stack `92.11.0` ships (not pinned separately)
- Actual Budget: `26.10.0-alpine` in `apps/actual-budget/deployment.yaml`
- Gmail Classifier: `0.1.0` in `apps/gmail-classifier/pyproject.toml`
- Drive Organizer: `0.1.0` in `apps/drive-organizer/pyproject.toml`
- Actual Classifier: `0.1.0` in `apps/actual-classifier/pyproject.toml`
- Alert Summarizer: `0.1.0` in `apps/alert-summarizer/pyproject.toml`
- homelab-ai library: `0.2.0` in `packages/homelab-ai/pyproject.toml`
- Astro: `7.4.2` in `docs/package.json`
- Starlight: `0.42.7` in `docs/package.json`
