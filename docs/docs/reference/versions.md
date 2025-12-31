---
sidebar_position: 1
title: Version Matrix
---

# Version Matrix

Keep these versions aligned when upgrading components.

:::note

Check the latest stable release before changing any pinned version.

:::

- Kubernetes: `v1.35` in `ansible/group_vars/all.yaml`
- Cilium: `1.18.5` in `ansible/group_vars/all.yaml`
- Cilium Helm chart: `1.18.5` in `infrastructure/cilium/cilium.yaml`
- containerd: `2.2.1` in `ansible/group_vars/all.yaml`
- ArgoCD: `v3.2.2` in `bootstrap/argocd/kustomization.yaml`
- ArgoCD Image Updater chart: `1.0.4` in `infrastructure/argocd-image-updater/argocd-image-updater.yaml`
- ArgoCD Image Updater app: `v1.0.2` in `infrastructure/argocd-image-updater/argocd-image-updater.yaml`
- Longhorn: `1.7.2` in `bootstrap/templates/longhorn.yaml`
- Tailscale Operator: `1.92.4` in `infrastructure/tailscale/tailscale-operator.yaml`
- Envoy Gateway: `v1.6.1` image tag in `infrastructure/envoy-gateway/envoy-gateway.yaml` (chart `v1.6.1`)
- Kubescape Operator chart: `1.30.0` in `infrastructure/kubescape/kubescape.yaml`
- Gateway API CRDs: `v1.4.1` in `infrastructure/gateway-api-crds/gateway-api-crds.yaml`
- Envoy Gateway CRDs: `v1.6.1` in `infrastructure/envoy-gateway-crds/`
- cert-manager: `v1.19.2` in `infrastructure/cert-manager/cert-manager.yaml`
- ExternalDNS chart: `1.19.0` in `infrastructure/external-dns/external-dns.yaml`
- External Secrets CRDs: `v1.2.0` in `infrastructure/external-secrets-crds/`
- External Secrets chart: `1.2.0` in `infrastructure/external-secrets/external-secrets.yaml`
- kube-prometheus-stack chart: `80.8.0` in `infrastructure/prometheus/prometheus.yaml`
- Prometheus Operator CRDs chart: `25.0.1` in `infrastructure/prometheus-operator-crds/prometheus-operator-crds.yaml`
- Metrics Server chart: `3.13.0` in `infrastructure/metrics-server/metrics-server.yaml`
- Vault chart: `0.31.0` in `infrastructure/vault/vault.yaml`
- Intel GPU plugin: `0.34.0` in `infrastructure/gpu/intel-plugin.yaml`
- NVIDIA GPU plugin: `0.17.0` in `infrastructure/gpu/nvidia-plugin.yaml`
