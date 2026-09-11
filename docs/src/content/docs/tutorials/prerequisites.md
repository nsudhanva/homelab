---
title: Prerequisites for Talos Linux Homelab
description: Set up your workstation with talosctl, kubectl, and Helm. Describe cluster machines in the Talos inventory and prepare the installer USB stick.
keywords:
  - talos prerequisites
  - talosctl installation
  - kubectl installation
  - helm installation
  - talos inventory
  - talos installer usb
  - ubuntu 26.04 workstation
sidebar:
  order: 2
---

# Prerequisites

Use this guide before the hardware tutorials. If you are following the local rehearsal path, use [Local Talos Cluster](./local-talos-cluster.md) instead.

## Step 1: Install workstation tooling

:::note

These tools run on your workstation. Cluster machines boot Talos Linux and are managed over the Talos API. No SSH access is used anywhere in this workflow.

:::

### macOS (Homebrew)

```bash
brew install qemu talosctl kubectl helm pre-commit
```

### Ubuntu 26.04 (APT)

```bash
sudo apt-get update && sudo apt-get install -y curl wget git qemu-system kubectl helm pre-commit
curl -sSL -o /usr/local/bin/talosctl https://github.com/siderolabs/talos/releases/download/v1.14.0/talosctl-linux-amd64
sudo chmod +x /usr/local/bin/talosctl
```

On ARM64 workstations, use the `talosctl-linux-arm64` binary instead.

### Ubuntu 26.04 container workstation

For a Linux-native shell on any host, run the repo workstation container:

```bash
./scripts/dev-container.sh up
./scripts/dev-container.sh shell
```

The container ships with Docker and the Kubernetes tooling above preinstalled.

## Step 2: Describe the machines

Update the machine list in `talos/nodes.yaml` with one entry per control plane and worker. Each entry carries a hostname, a LAN IP, and the install disk. The control plane endpoint is the address clients and workloads use to reach the API.

If you use Tailscale, the node IPs can be tailnet addresses once the operator is running. For the initial bootstrap, use LAN IPs.

## Step 3: Flash the installer USB

Print the installer ISO URL for the pinned schematic and write it to a USB stick:

```bash
./scripts/talos-baremetal.sh iso-url
```

Boot each machine from the stick. Machines start in maintenance mode and wait for configuration. No OS installation steps run by hand.

## Step 4: Confirm versions

Check the pinned component versions in `talos/versions.yaml` and the full matrix in [Version Matrix](../reference/versions.md). All install and upgrade flows read from these files.

## What you still do manually

After the workstation is ready, continue with:

- Prepare boot media in [Boot Media](./system-prep.md).
- Render machine configuration in [Machine Configuration](./containerd.md).
- Bootstrap the cluster in [Talos Bootstrap](./kubernetes.md).
- Install ArgoCD and apply the bootstrap in [ArgoCD and GitOps](./argocd.md).
- Add workers with [Add Workers](./join-workers.md).
