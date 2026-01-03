---
sidebar_position: 1
title: Prerequisites
description: Workstation setup and Ansible inventory prep for building a bare-metal Kubernetes cluster.
keywords:
  - bare metal kubernetes
  - workstation setup
  - ansible inventory
  - kubeadm
  - ubuntu 24.04
---

# Prerequisites

Use this guide before the bare metal tutorials. If you are following the local VM path, use [Local Multipass Cluster](./local-multipass-cluster.md) instead.

## Step 1: Install workstation tooling

:::note

These tools are installed on your workstation. The Ansible provisioning playbooks configure the cluster nodes and do not install local tooling.

:::

### macOS (Homebrew)

```bash
brew install ansible kubectl helm pre-commit
```

### Ubuntu

```bash
sudo apt update
sudo add-apt-repository ppa:quentiumyt/nvtop
sudo apt install -y curl wget git pre-commit python3 python3-dev htop nvtop dmsetup npm nodejs
curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
sudo apt-get update
sudo apt-get install -y helm
```

## Step 2: Prepare Ansible inventory

Update the node list and user in `ansible/inventory/hosts.yaml`, then confirm versions and paths in `ansible/group_vars/all.yaml`.
If you are using Tailscale, set `ansible_host` to the Tailscale IP or MagicDNS hostname.

## Step 3: Run Ansible provisioning

Run this from the repository root so the relative paths resolve correctly.

:::note

If you are doing a fully manual setup, skip this step and follow [System Preparation](./system-prep.md) and [Install Containerd](./containerd.md) before [Kubernetes](./kubernetes.md).

:::

```bash
ansible-playbook -i ansible/inventory/hosts.yaml \
  ansible/playbooks/provision-cpu.yaml \
  -e @ansible/group_vars/all.yaml
```

If you need GPU support, use `ansible/playbooks/provision-intel-gpu.yaml` or `ansible/playbooks/provision-nvidia-gpu.yaml`.

## What the provisioning playbook does

The provisioning playbooks run these roles on each node:

- `base`: disables swap, loads kernel modules, writes sysctl and inotify settings, installs base packages
- `containerd`: installs containerd (upstream or apt), writes `/etc/containerd/config.toml`, enables the service
- `kubernetes`: adds the Kubernetes apt repo, installs kubeadm/kubelet/kubectl, pins versions, enables kubelet
- `longhorn-prereqs`: installs open-iscsi, nfs-common, cryptsetup, and creates the Longhorn data path
- `tailscale`: installs `tailscaled` and enables the service

The NVIDIA playbook also runs the `nvidia-gpu` role.

## What you still do manually

After provisioning, continue with:

- Initialize the control plane with `kubeadm init` in [Kubernetes](./kubernetes.md).
- Install Cilium in [Cilium CNI](./cilium.md).
- Install ArgoCD and apply the bootstrap in [ArgoCD and GitOps](./argocd.md).
- Join workers with [Join Worker Nodes](./join-workers.md).
- If you want node-level tailnet access, run `sudo tailscale up` as described in [Add a Worker Node](../how-to/add-worker-node.md).
