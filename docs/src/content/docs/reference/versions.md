---
title: Component Version Matrix
description: Reference matrix of all pinned component versions including Talos Linux, Kubernetes, Cilium, ArgoCD, Longhorn, and other infrastructure tools with their configuration file locations.
keywords:
  - talos version
  - kubernetes version
  - cilium version
  - argocd version
  - longhorn version
  - helm chart versions
  - kubernetes component versions
sidebar:
  order: 3
---

# Version Matrix

Keep these versions aligned when upgrading components.

:::note

Check the latest stable release before changing any pinned version.

:::

- Talos Linux: `v1.14.0` in `talos/versions.yaml`
- Kubernetes: `v1.37.0` in `talos/versions.yaml`
- containerd: `2.3.4` via the Talos release
- Ubuntu workstation: `26.04` in `talos/versions.yaml`
- Cilium Helm chart: `1.20.1` in `infrastructure/cilium/cilium.yaml`
- ArgoCD: `v3.5.2` in `bootstrap/argocd/kustomization.yaml`
- ArgoCD Image Updater chart: `1.3.1` in `infrastructure/argocd-image-updater/argocd-image-updater.yaml`
- Longhorn: `1.12.1` in `bootstrap/templates/longhorn.yaml`
- Tailscale Operator: `1.102.3` in `infrastructure/tailscale/tailscale-operator.yaml`
- Envoy Gateway: `v1.9.1` chart in `infrastructure/envoy-gateway/envoy-gateway.yaml`
- Kubescape Operator chart: `1.40.4` in `infrastructure/kubescape/kubescape.yaml`
- Gateway API CRDs: `v1.6.2` in `infrastructure/gateway-api-crds/gateway-api-crds.yaml`
- Envoy Gateway CRDs: `v1.9.1` in `infrastructure/envoy-gateway-crds/`
- cert-manager: `v1.21.2` in `infrastructure/cert-manager/cert-manager.yaml`
- ExternalDNS chart: `1.22.0` in `infrastructure/external-dns/external-dns.yaml`
- External Secrets CRDs: `v2.10.0` in `infrastructure/external-secrets-crds/`
- External Secrets chart: `2.10.0` in `infrastructure/external-secrets/external-secrets.yaml`
- kube-prometheus-stack chart: `90.1.1` in `infrastructure/prometheus/prometheus.yaml`
- Prometheus Operator CRDs chart: `32.0.0` in `infrastructure/prometheus-operator-crds/prometheus-operator-crds.yaml`
- Metrics Server chart: `3.14.0` in `infrastructure/metrics-server/metrics-server.yaml`
- Vault chart: `0.34.1` in `infrastructure/vault/vault.yaml`
- NVIDIA GPU Operator chart: `v26.7.0` in `infrastructure/gpu-operator/gpu-operator.yaml`
- Intel GPU plugin: `0.36.0` in `infrastructure/gpu/intel-plugin.yaml`
- NVIDIA device plugin: `v0.20.0` in `infrastructure/gpu/nvidia-plugin.yaml`
- ntfy: `v2.28.0` in `infrastructure/ntfy/deployment.yaml`
- CoreDNS: `1.14.7` in `infrastructure/tailscale-dns/deployment.yaml`
- Homer: `v26.08.3` in `apps/homer/deployment.yaml`
- Headlamp: `v0.45.0` in `apps/headlamp/deployment.yaml`
