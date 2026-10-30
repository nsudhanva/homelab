---
title: K3s Cluster Provisioning and Bootstrap
description: Run the Ansible provisioning playbook to install K3s, Flannel, local-path storage, and NVIDIA CDI, and to bootstrap ArgoCD.
keywords:
  - k3s bootstrap
  - ansible k3s installation
  - bare metal kubernetes
  - local-path storage
  - nvidia cdi k3s
sidebar:
  order: 5
---

In this tutorial, you provision the K3s control plane on the bare-metal node and start the GitOps control loop.

## Step 1: Run the Ansible provisioning playbook

From your workstation, run the provisioning script:

```bash
./scripts/provision.sh
```

To run the playbook without the script, use this command:

```bash
ansible-playbook -i ansible/inventory/hosts.yaml ansible/site.yaml
```

The playbook runs these roles in this order:

- `common` (OS and kernel settings): Installs the base packages, loads `overlay` and `br_netfilter`, and sets the bridge, IP forwarding, and inotify sysctls. It creates `/home/k3s-storage` with mode `0700`. It sets the CPU power profile to `power_profile` (`balanced`) with `power-profiles-daemon`, so that idle cores run at a lower clock speed.
- `tailscale` (Tailscale): Fails if Tailscale is not installed. It turns off Tailscale DNS on the node (`tailscale set --accept-dns=false`) and waits until `tailscale0` has the node IP.
- `nvidia` (NVIDIA GPU): Fails if `nvidia-smi` does not run. It adds the NVIDIA repository, installs `nvidia-container-toolkit` and `runc`, and generates the CDI specification at `/etc/cdi/nvidia.yaml`.
- `k3s_server` (K3s server): Writes `/etc/rancher/k3s/config.yaml` and a systemd drop-in that starts K3s after `tailscaled`. If `/usr/local/bin/k3s` does not exist, it installs K3s `v1.37.1+k3s1`. If K3s is installed, the role does not upgrade it, because the System Upgrade Controller does upgrades. The config disables Traefik, ServiceLB, and the bundled metrics-server, keeps Flannel as the CNI, and sets the local-path storage root.
- Kubeconfig retrieval (in `k3s_server`): Copies the cluster kubeconfig to your workstation as `k3s.kubeconfig`. It sets the server address to the Tailscale IP of the node.
- `argocd` (ArgoCD bootstrap): From your workstation, applies `bootstrap/argocd` with server-side apply. It waits for `argocd-server`, and then applies the root application `bootstrap/root.yaml`.

## Step 2: Validate the control plane node

Make sure that the control plane node reports `Ready`:

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

Make sure that the NVIDIA GPU Operator registered the GPU. ArgoCD deploys the GPU Operator from `infrastructure/gpu/`. Thus, the value shows only after the `infra-gpu` application syncs.

```bash
kubectl get node legion -o jsonpath='{.status.allocatable.nvidia\.com/gpu}'
```

The output must be `1`.

## Step 4: Examine the core system pods

Make sure that all pods in `kube-system` and `argocd` are in the `Running` state:

```bash
kubectl get pods -A
```

## Step 5: Next steps

Go to [ArgoCD and GitOps](/tutorials/argocd/). That tutorial shows how ArgoCD manages the infrastructure components and the user workloads.
