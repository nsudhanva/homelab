---
title: K3s Cluster Provisioning and Bootstrap
description: Execute the Ansible provisioning playbook to install K3s, Flannel CNI, Local-Path storage, NVIDIA CDI, and bootstrap ArgoCD.
keywords:
  - k3s bootstrap
  - ansible k3s installation
  - bare metal kubernetes
  - local-path storage
  - nvidia cdi k3s
sidebar:
  order: 5
---

# K3s Bootstrap

This tutorial guides you through provisioning the bare-metal K3s control plane and bootstrapping the GitOps control loop.

## Step 1: Run the Ansible provisioning playbook

Execute the unified provisioning script or run `ansible-playbook` directly from your workstation:

```bash
./scripts/provision.sh
```

Or execute the playbook manually:

```bash
ansible-playbook -i ansible/inventory/hosts.yaml ansible/site.yaml
```

The playbook executes the complete lifecycle automatically:

- **OS & Kernel Tuning**: Loads `overlay` and `br_netfilter`, configures bridge iptables sysctl flags, and ensures `/home/k3s-storage` exists.
- **NVIDIA GPU Integration**: Adds NVIDIA repositories, installs `nvidia-container-toolkit`, and generates OCI CDI specifications at `/etc/cdi/nvidia.yaml`.
- **K3s Server Installation**: Installs K3s `v1.36.4+k3s1`, applies `/etc/rancher/k3s/config.yaml` with Flannel CNI and local-path storage, and registers the systemd service.
- **Kubeconfig Retrieval**: Copies the cluster kubeconfig to your workstation as `k3s.kubeconfig` and configures the external Tailscale endpoint.
- **ArgoCD Bootstrap**: Applies the ArgoCD manifests via server-side apply and reconciles the root application `bootstrap/root.yaml`.

## Step 2: Validate the control plane node

Verify that the control plane node reports `Ready`:

```bash
export KUBECONFIG=$PWD/k3s.kubeconfig
kubectl get nodes -o wide
```

Expected output:

```text
NAME     STATUS   ROLES           AGE   VERSION
legion   Ready    control-plane   10m   v1.36.4+k3s1
```

## Step 3: Verify GPU allocatable resource

Confirm that the NVIDIA GPU Operator or local device plugin registered the GPU:

```bash
kubectl get node legion -o jsonpath='{.status.allocatable.nvidia\.com/gpu}'
```

Expected output is `1`.

## Step 4: Verify core system pods

Confirm that all system pods in `kube-system` and `argocd` are running:

```bash
kubectl get pods -A
```

## Step 5: Next steps

Proceed to [ArgoCD and GitOps](./argocd.md) to understand how the GitOps engine manages infrastructure components and user workloads.
