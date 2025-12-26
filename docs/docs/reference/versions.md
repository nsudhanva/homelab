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
- Longhorn: `1.7.2` in `bootstrap/templates/longhorn.yaml`
- Tailscale Operator: `1.78.3` in `infrastructure/tailscale/tailscale-operator.yaml`
- Intel GPU plugin: `0.34.0` in `infrastructure/gpu/intel-plugin.yaml`
- NVIDIA GPU plugin: `0.17.0` in `infrastructure/gpu/nvidia-plugin.yaml`
