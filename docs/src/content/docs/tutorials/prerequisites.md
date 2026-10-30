---
title: Prerequisites for Bare-Metal K3s Homelab
description: Install Ansible, kubectl, and pre-commit on the operator workstation. Prepare SSH access and the accounts for the bare-metal K3s cluster.
keywords:
  - k3s prerequisites
  - ansible installation
  - kubectl installation
  - bare metal cluster prerequisites
  - ubuntu 26.04 setup
sidebar:
  order: 2
---

Prepare the operator workstation before you provision the cluster. Then make sure that the workstation can connect to the target node.

## Step 1: Install workstation tooling

Install Ansible, `kubectl`, and `pre-commit` on the workstation.

### macOS (Homebrew)

```bash
brew install ansible kubectl pre-commit
```

### Linux (APT)

The Ubuntu archive does not contain `kubectl`. Install the other tools with APT. Then download `kubectl` from `dl.k8s.io`.

```bash
sudo apt-get update && sudo apt-get install -y curl git ansible pre-commit
curl -sSLo kubectl "https://dl.k8s.io/release/v1.37.1/bin/linux/amd64/kubectl"
sudo install -m 0755 kubectl /usr/local/bin/kubectl
```

ArgoCD installs every Helm chart in this repository. The workstation does not need Helm.

### Dev Container Workstation

You can also use the workstation container in this repository. Refer to [Ubuntu Workstation](/tutorials/workstation/).

```bash
./scripts/dev-container.sh up
./scripts/dev-container.sh shell
```

## Step 2: Configure SSH access to the host

Ansible connects to the node over SSH. If you do not have an SSH key pair, create one.

```bash
ssh-keygen -t ed25519 -C "homelab-admin"
```

Copy your public key to the node `legion`. Use the Tailscale IP `100.66.139.118` or the LAN IP.

```bash
ssh-copy-id sudhanva@100.66.139.118
```

On the node, add the user to the `sudo` group. Then give the user passwordless sudo.

```bash
sudo usermod -aG sudo sudhanva
echo "sudhanva ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/sudhanva
```

## Step 3: Gather account credentials

Get these credentials before you continue:

- Tailscale: an OAuth client secret with permission to manage Tailscale devices and the Kubernetes operator resources.
- Cloudflare: an API token with Zone.DNS edit permission for the managed domain (`sudhanva.me`).
- GitHub: a personal access token for ArgoCD repository access and ArgoCD Image Updater write-back (Vault `kv/argocd/repo-creds`).
- Container registry: a GHCR read token. ArgoCD Image Updater uses it to check tags (Vault `kv/argocd-image-updater/ghcr`). Image Updater reads Docker Hub anonymously.

## Step 4: Next steps

When the workstation tools and the SSH access operate correctly, continue with these tutorials:

- Prepare the bare-metal machine in [Host Preparation](/tutorials/system-prep/).
- Configure the Ansible variables in [Ansible Configuration](/tutorials/containerd/).
- Bootstrap the cluster in [K3s Bootstrap](/tutorials/kubernetes/).
