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

The playbook runs these roles in order:

- **OS & Kernel Tuning (`common`)**: It installs base packages, loads `overlay` and `br_netfilter`, and sets the bridge, IP forwarding, and inotify sysctls. It also makes sure that `/home/k3s-storage` exists with mode `0700`, and sets the CPU power profile to `power_profile` (`balanced`) with `power-profiles-daemon`, so idle cores clock down instead of staying in turbo.
- **Tailscale (`tailscale`)**: It fails if Tailscale is not installed. It turns off Tailscale DNS on the node (`tailscale set --accept-dns=false`) and waits until `tailscale0` has the node IP.
- **NVIDIA GPU Integration (`nvidia`)**: It fails if `nvidia-smi` does not run. It adds the NVIDIA repository, installs `nvidia-container-toolkit` and `runc`, and generates the CDI specification at `/etc/cdi/nvidia.yaml`.
- **K3s Server Installation (`k3s_server`)**: It writes `/etc/rancher/k3s/config.yaml` and a systemd drop-in that starts K3s after `tailscaled`. If `/usr/local/bin/k3s` does not exist, it installs K3s `v1.37.1+k3s1`. If K3s is already installed, the playbook does not upgrade it. The System Upgrade Controller handles upgrades. The config disables Traefik, ServiceLB, and the bundled metrics-server, keeps Flannel as the CNI, and sets the local-path storage root.
- **Kubeconfig Retrieval**: It copies the cluster kubeconfig to your workstation as `k3s.kubeconfig` and sets the server address to the Tailscale IP of the node.
- **ArgoCD Bootstrap (`argocd`)**: From your workstation, it applies `bootstrap/argocd` with server-side apply, waits for `argocd-server`, and applies the root application `bootstrap/root.yaml`.

## Step 2: Validate the control plane node

Make sure that the control plane node reports `Ready`.

```bash
export KUBECONFIG=$PWD/k3s.kubeconfig
kubectl get nodes -o wide
```

The output is similar to this:

```text
NAME     STATUS   ROLES           AGE   VERSION
legion   Ready    control-plane   10m   v1.37.1+k3s1
```

## Step 3: Examine the GPU allocatable resource

Make sure that the NVIDIA GPU Operator registered the GPU. ArgoCD deploys the GPU Operator from `infrastructure/gpu/`, so this value appears only after the `infra-gpu` application syncs.

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

Go to [ArgoCD and GitOps](/tutorials/argocd/). That tutorial tells how the GitOps engine manages infrastructure components and user workloads.
