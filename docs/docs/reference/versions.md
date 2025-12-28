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
- containerd: `2.2.1` in `ansible/group_vars/all.yaml`
- Longhorn: `1.7.2` in `bootstrap/templates/longhorn.yaml`
- Tailscale Operator: `1.92.4` in `infrastructure/tailscale/tailscale-operator.yaml`
- Envoy Gateway: `v1.6.1` image tag in `infrastructure/envoy-gateway/envoy-gateway.yaml` (chart `v0.0.0-latest`)
- Gateway API CRDs: `v1.4.1` in `infrastructure/gateway-api-crds/`
- cert-manager: `v1.19.2` in `infrastructure/cert-manager/cert-manager.yaml`
- ExternalDNS chart: `1.19.0` in `infrastructure/external-dns/external-dns.yaml`
- External Secrets chart: `1.2.0` in `infrastructure/external-secrets/external-secrets.yaml`
- Vault chart: `0.31.0` in `infrastructure/vault/vault.yaml`
- Intel GPU plugin: `0.34.0` in `infrastructure/gpu/intel-plugin.yaml`
- NVIDIA GPU plugin: `0.17.0` in `infrastructure/gpu/nvidia-plugin.yaml`
