---
title: Prerequisites for Bare-Metal K3s Homelab
description: Set up your operator workstation with Ansible, kubectl, and Helm. Prepare SSH access and accounts for the bare-metal K3s cluster.
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

Before provisioning the bare-metal K3s cluster, set up your local operator workstation and verify target node access.

## Step 1: Install workstation tooling

Ensure your local workstation has the necessary automation and Kubernetes management tools installed:

### macOS (Homebrew)

```bash
brew install ansible kubectl helm pre-commit
```

### Linux (APT)

```bash
sudo apt-get update && sudo apt-get install -y curl git ansible kubectl helm pre-commit
```

### Dev Container Workstation

Alternatively, run the repo's containerized workstation environment:

```bash
./scripts/dev-container.sh up
./scripts/dev-container.sh shell
```

## Step 2: Configure SSH access to the host

Ansible manages bare-metal nodes over SSH. Generate an SSH key pair if you do not already have one:

```bash
ssh-keygen -t ed25519 -C "homelab-admin"
```

Copy your public key to the target node `legion` (`100.66.139.118` or your LAN IP):

```bash
ssh-copy-id sudhanva@100.66.139.118
```

Verify passwordless sudo on the target host by adding the user to `sudoers`:

```bash
sudo usermod -aG sudo sudhanva
echo "sudhanva ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/sudhanva
```

## Step 3: Gather account credentials

Have the following credentials ready for platform integration:

- **Tailscale**: An OAuth client secret with permissions to manage Tailscale devices and Kubernetes operator resources.
- **Cloudflare**: An API token with Zone.DNS edit permissions for your managed domain (`sudhanva.me`).
- **GitHub**: A personal access token for Git authentication and ArgoCD Image Updater write-back.

## Step 4: Next steps

Once your workstation tools and target host SSH access are verified, proceed to:

- Prepare the bare-metal machine in [Host Preparation](./system-prep.md).
- Configure Ansible variables in [Ansible Configuration](./containerd.md).
- Bootstrap the cluster in [K3s Bootstrap](./kubernetes.md).
