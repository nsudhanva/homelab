---
title: Local Talos Cluster with QEMU
description: Create a local Talos Linux Kubernetes cluster using QEMU virtual machines for development and testing. Validate Talos machine configuration and cluster bootstrap before deploying to hardware.
keywords:
  - talos local cluster
  - talos qemu
  - local kubernetes cluster
  - kubernetes development environment
  - talos development
  - kubernetes testing
  - rehearsal cluster
sidebar:
  order: 9
---

# Local Talos Cluster

This tutorial runs a Talos Linux cluster in local QEMU virtual machines. It is intended as an optional rehearsal path before the hardware setup, and mirrors the same machine configuration shape.

## Quick Start (Automated)

Use the automation script for a one-command setup:

```bash
./scripts/talos-local.sh up
```

This handles everything: QEMU VM creation, machine configuration, cluster bootstrap, kubeconfig, and smoke testing.

For a low-resource rehearsal, run a single-node control plane:

```bash
WORKER_COUNT=0 CP_CPUS=2 CP_MEMORY=2G ./scripts/talos-local.sh up
```

When done:

```bash
./scripts/talos-local.sh down
```

---

## Manual Setup (Step by Step)

If you prefer to understand each step or need to customize the process, follow the manual instructions below.

### Prerequisites

- QEMU installed on your workstation
- talosctl installed on your workstation
- kubectl installed on your workstation
- Root access for the cluster create step (QEMU networking requirement)
- A single-node rehearsal expects around 6GB of free RAM

### Step 1: Install host tools

macOS (Homebrew):

```bash
brew install qemu talosctl kubectl helm
```

Ubuntu 26.04 (APT):

```bash
sudo apt-get update && sudo apt-get install -y qemu-system kubectl helm
curl -sSL -o /usr/local/bin/talosctl https://github.com/siderolabs/talos/releases/download/v1.14.0/talosctl-linux-amd64
sudo chmod +x /usr/local/bin/talosctl
```

On ARM64 workstations, use the `talosctl-linux-arm64` binary instead.

### Step 2: Create the rehearsal cluster

```bash
sudo -E talosctl cluster create dev \
  --workers 0 \
  --cpus 2 \
  --memory 2048 \
  --kubernetes-version 1.37.0 \
  --talos-version v1.14.0
```

The command generates configuration under `_out/`, boots the VMs, bootstraps etcd, and writes kubeconfig and talosconfig next to the generated files.

### Step 3: Point tooling at the cluster

```bash
export KUBECONFIG=$PWD/_out/kubeconfig
export TALOSCONFIG=$PWD/_out/talosconfig
kubectl get nodes -o wide
```

### Step 4: Apply the Cilium patch shape

The rehearsal uses the same configuration shape as hardware: no built-in CNI, no kube-proxy. Apply the repo patches to confirm they render:

```bash
talosctl gen machineconfig \
  --with-secrets _out/secrets.yaml \
  --talos-version v1.14.0 \
  --kubernetes-version 1.37.0 \
  --config-patch @talos/patches/common.yaml \
  --output-dir /tmp/talos-patch-check
```

### Step 5: Verify the cluster

```bash
kubectl apply -f talos/test/deployment.yaml
kubectl apply -f talos/test/service.yaml
kubectl get pods -l app=test-nginx
```

### Step 6: Tear down

```bash
sudo -E talosctl cluster destroy --provisioner qemu
```

---

## Next Steps

When ready for real hardware:

- [Prerequisites](./prerequisites.md) - Hardware and network requirements
- [System Preparation](./system-prep.md) - Boot media and installer image
- [Talos Bootstrap](./kubernetes.md) - Cluster bootstrap on hardware

The Talos machine configuration and GitOps layout are identical; only the machine inventory changes.
