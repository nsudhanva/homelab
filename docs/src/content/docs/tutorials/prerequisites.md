---
title: Prerequisites for Bare-Metal K3s Homelab
description: Install Ansible, kubectl, and Helm on your operator workstation. Prepare SSH access and accounts for the bare-metal K3s cluster.
keywords:
  - k3s prerequisites
  - ansible installation
  - kubectl installation
  - bare metal cluster prerequisites
  - ubuntu 26.04 setup
sidebar:
  order: 2
---

# Prerequisites

Before you provision the bare-metal K3s cluster, prepare your local operator workstation. Then make sure that you can connect to the target node.

## Step 1: Install workstation tooling

Install the automation and Kubernetes management tools on your local workstation:

### macOS (Homebrew)

```bash
brew install ansible kubectl helm pre-commit
```

### Linux (APT)

```bash
sudo apt-get update && sudo apt-get install -y curl git ansible kubectl helm pre-commit
```

### Dev Container Workstation

Alternatively, use the containerized workstation environment in the repo:

```bash
./scripts/dev-container.sh up
./scripts/dev-container.sh shell
```

## Step 2: Configure SSH access to the host

Ansible manages bare-metal nodes over SSH. If you do not have an SSH key pair, make one:

```bash
ssh-keygen -t ed25519 -C "homelab-admin"
```

Copy your public key to the target node `legion` (`100.66.139.118` or your LAN IP):

```bash
ssh-copy-id sudhanva@100.66.139.118
```

On the target host, add the user to `sudoers` to get passwordless sudo:

```bash
sudo usermod -aG sudo sudhanva
echo "sudhanva ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/sudhanva
```

## Step 3: Gather account credentials

Get these credentials before you start the platform integration:

- Tailscale: An OAuth client secret with permissions to manage Tailscale devices and Kubernetes operator resources.
- Cloudflare: An API token with Zone.DNS edit permissions for your managed domain (`sudhanva.me`).
- GitHub: A personal access token for Git authentication and ArgoCD Image Updater write-back.

## Step 4: Next steps

When your workstation tools and SSH access to the target host operate correctly, go to these pages:

- Prepare the bare-metal machine in [Host Preparation](./system-prep.md).
- Configure Ansible variables in [Ansible Configuration](./containerd.md).
- Bootstrap the cluster in [K3s Bootstrap](./kubernetes.md).
