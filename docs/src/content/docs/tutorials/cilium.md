---
title: Cilium CNI with kube-proxy Replacement
description: Run Cilium as the Container Network Interface for Kubernetes with eBPF-based kube-proxy replacement and Hubble observability, deployed through ArgoCD GitOps.
keywords:
  - cilium installation
  - cilium cni
  - kube-proxy replacement
  - ebpf kubernetes
  - hubble observability
  - kubernetes networking
  - cilium tailscale
  - socketlb hostnamespaceonly
sidebar:
  order: 6
---

# Cilium CNI

Cilium provides the Container Network Interface (CNI) and replaces kube-proxy with eBPF-based load balancing. Talos ships no CNI and no kube-proxy in this setup, so Cilium is the only networking dataplane.

## Step 1: Confirm the machine configuration

Talos must not deploy Flannel or kube-proxy. The repo patches in `talos/patches/` delete the Flannel configuration document and disable the kube-proxy configuration document on every render. Verify a rendered config before bootstrapping hardware or rehearsing locally.

## Step 2: Review the Helm values

Cilium deploys from `infrastructure/cilium/` through the `infra-cilium` ArgoCD Application. The values in `infrastructure/cilium/values.cilium` carry the settings this stack needs:

- `kubeProxyReplacement: true` moves service routing into eBPF
- `socketLB.hostNamespaceOnly: true` keeps Tailscale operator LoadBalancer services working
- `routingMode: tunnel` with VXLAN encapsulation for the pod network
- `k8sServiceHost` points at the control plane endpoint

:::warning

The `socketLB.hostNamespaceOnly=true` setting is **required** when using Tailscale Kubernetes Operator LoadBalancer services. Without it, traffic forwarded through the Tailscale proxy pod will fail because Cilium's socket-level load balancer interferes with iptables DNAT rules.

:::

## Step 3: Let ArgoCD deploy it

No manual install command is used. After [ArgoCD and GitOps](./argocd.md) applies the root Application, the `infra-cilium` Application syncs the pinned chart version from `talos/versions.yaml`.

## Step 4: Verify installation

```bash
kubectl -n kube-system get pods -l app.kubernetes.io/name=cilium-agent
kubectl -n kube-system exec ds/cilium -- cilium status --brief
kubectl -n kube-system exec ds/cilium -- cilium config view | grep -E "bpf-lb-sock|kubeProxyReplacement"
```

Expected output includes:

```text
bpf-lb-sock-hostns-only    true
kubeProxyReplacement       true
```

Nodes move to Ready once the Cilium agents report healthy.

## Upgrading Cilium

To update Cilium, bump the pinned version in `talos/versions.yaml` and in `infrastructure/cilium/cilium.yaml`, then push. ArgoCD rolls the DaemonSet.

:::note

After upgrading Cilium, restart any pods that depend on the new network configuration (e.g., Tailscale proxy pods).

:::
