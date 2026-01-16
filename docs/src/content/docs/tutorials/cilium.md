---
title: Install Cilium CNI with kube-proxy Replacement
description: Install Cilium as the Container Network Interface for Kubernetes with eBPF-based kube-proxy replacement and Hubble observability enabled.
keywords:
  - cilium installation
  - cilium cni
  - kube-proxy replacement
  - ebpf kubernetes
  - hubble observability
  - cilium cli
  - kubernetes networking
  - cilium tailscale
  - socketlb hostnamespaceonly
sidebar:
  order: 6
---

# Cilium CNI

Cilium provides the Container Network Interface (CNI) and replaces kube-proxy with eBPF-based load balancing.

:::note

Ansible does not install Cilium. Run these steps after the control plane is initialized.

:::

## Step 1: Install Cilium CLI

```bash
CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
curl -L --fail --remote-name-all \
  https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz{,.sha256sum}
sha256sum --check cilium-linux-amd64.tar.gz.sha256sum
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz{,.sha256sum}
```

## Step 2: Install Cilium with kube-proxy replacement

Get the version from `ansible/group_vars/all.yaml`:

```bash
CILIUM_VERSION=$(grep -E "cilium_version:" ansible/group_vars/all.yaml | head -n 1 | awk -F'"' '{print $2}')
```

Update `k8sServiceHost` in `infrastructure/cilium/values.cilium` to match the control plane IP.

Install with the required settings for Tailscale compatibility:

```bash
cilium install --version $CILIUM_VERSION --values infrastructure/cilium/values.cilium
```

:::warning

The `socketLB.hostNamespaceOnly=true` setting is **required** when using Tailscale Kubernetes Operator LoadBalancer services. Without it, traffic forwarded through the Tailscale proxy pod will fail because Cilium's socket-level load balancer interferes with iptables DNAT rules.

:::

Remove the kube-proxy DaemonSet since Cilium replaces it:

```bash
kubectl -n kube-system delete daemonset kube-proxy
```

## Step 3: Enable Hubble observability

```bash
cilium hubble enable --ui
```

## Step 4: Verify installation

```bash
kubectl get nodes
cilium status
cilium config view | grep -E "bpf-lb-sock|kubeProxyReplacement"
```

Expected output should include:

```text
bpf-lb-sock-hostns-only    true
kubeProxyReplacement       true
```

## Upgrading Cilium

To update Cilium settings after initial installation:

```bash
cilium upgrade --version $CILIUM_VERSION --set socketLB.hostNamespaceOnly=true
kubectl rollout restart daemonset/cilium -n kube-system
kubectl rollout status daemonset/cilium -n kube-system
```

:::note

After upgrading Cilium, restart any pods that depend on the new network configuration (e.g., Tailscale proxy pods).

:::
