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

## Step 3: Run Ansible provisioning

Run this from the repository root so the relative paths resolve correctly.

```bash
ansible-playbook -i ansible/inventory/hosts.yaml \
  ansible/playbooks/provision-cpu.yaml \
  -e @ansible/group_vars/all.yaml
```

If you need GPU support, use `ansible/playbooks/provision-intel-gpu.yaml` or `ansible/playbooks/provision-nvidia-gpu.yaml`.
