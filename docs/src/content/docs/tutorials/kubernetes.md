---
title: K3s Cluster Provisioning and Bootstrap
description: Run the Ansible provisioning playbook to install K3s, Flannel CNI, Local-Path storage, and NVIDIA CDI, and to bootstrap ArgoCD.
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

In this tutorial, you provision the bare-metal K3s control plane and bootstrap the GitOps control loop.

## Step 1: Run the Ansible provisioning playbook

From your workstation, run the unified provisioning script or run `ansible-playbook` directly.

```bash
./scripts/provision.sh
```

To run the playbook manually, use this command.

```bash
ansible-playbook -i ansible/inventory/hosts.yaml ansible/site.yaml
```

The playbook does the full lifecycle automatically.

- **OS & Kernel Tuning**: It loads `overlay` and `br_netfilter` and configures the bridge iptables sysctl flags. It also makes sure that `/home/k3s-storage` exists.
- **NVIDIA GPU Integration**: It adds the NVIDIA repositories and installs `nvidia-container-toolkit`. It generates the OCI CDI specifications at `/etc/cdi/nvidia.yaml`.
- **K3s Server Installation**: It installs K3s `v1.36.4+k3s1` and applies `/etc/rancher/k3s/config.yaml` with Flannel CNI and local-path storage. It registers the systemd service.
- **Kubeconfig Retrieval**: It copies the cluster kubeconfig to your workstation as `k3s.kubeconfig` and configures the external Tailscale endpoint.
- **ArgoCD Bootstrap**: It applies the ArgoCD manifests with server-side apply and reconciles the root application `bootstrap/root.yaml`.

## Step 2: Validate the control plane node

Make sure that the control plane node reports `Ready`.

```bash
export KUBECONFIG=$PWD/k3s.kubeconfig
kubectl get nodes -o wide
```

The output is similar to this:

```text
NAME     STATUS   ROLES           AGE   VERSION
legion   Ready    control-plane   10m   v1.36.4+k3s1
```

## Step 3: Examine the GPU allocatable resource

Make sure that the NVIDIA GPU Operator or the local device plugin registered the GPU.

```bash
kubectl get node legion -o jsonpath='{.status.allocatable.nvidia\.com/gpu}'
```

The output must be `1`.

## Step 4: Examine the core system pods

Make sure that all system pods in `kube-system` and `argocd` run.

```bash
kubectl get pods -A
```

## Step 5: Next steps

Go to [ArgoCD and GitOps](./argocd.md). That tutorial tells how the GitOps engine manages infrastructure components and user workloads.
