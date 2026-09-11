---
title: Build Talos Cluster from Scratch
description: Complete guide to building a Talos Linux Kubernetes cluster from blank hardware. Covers the installer image, declarative machine configuration, cluster bootstrap, ArgoCD GitOps, and Vault secrets management.
keywords:
  - talos linux from scratch
  - build kubernetes cluster
  - talos cluster setup
  - talos machine configuration
  - argocd gitops bootstrap
  - cilium cni setup
  - kubernetes homelab
  - production kubernetes cluster
sidebar:
  order: 1
---

# From Scratch

Use this guide to build a homelab cluster from blank hardware using this repo as the source of truth. One scripted flow takes a fresh laptop from installer USB to a running GitOps-managed cluster.

## Step 1: Prepare the workstation

Follow [Prerequisites](../tutorials/prerequisites.md) to install tooling and describe your machines in `talos/nodes.yaml`.

## Step 2: Flash the installer image

Get the installer ISO URL for the pinned schematic:

```bash
./scripts/talos-baremetal.sh iso-url
```

Write the ISO to a USB stick and boot the laptop from it. The machine starts in maintenance mode and waits for configuration over the Talos API. There is nothing to install by hand.

## Step 3: Bring up the whole cluster

Run the bootstrap from the repo root:

```bash
./scripts/talos-baremetal.sh up
```

The script generates secrets on first run, renders machine configuration from `talos/nodes.yaml` and the patches in `talos/patches/`, applies it to every machine, bootstraps etcd, fetches kubeconfig, installs ArgoCD, and applies the root Application. Re-running it is safe: it converges instead of duplicating work.

If you need GPU support, add the worker to `talos/nodes.yaml` and follow [GPU Support](../how-to/gpu.md) after bootstrap.

## Step 4: Configure Vault and External Secrets

Follow [Vault](../how-to/vault.md) to initialize Vault and create the required secrets for ExternalDNS, cert-manager, and the Tailscale operator.

## Step 5: Validate the cluster

```bash
talosctl -n <control-plane-ip> get members
kubectl get nodes
kubectl get pods -A
kubectl get apps -n argocd
```

## Local rehearsal

Use this for a local dry run before touching hardware. It creates a Talos QEMU cluster with the same machine configuration shape:

```bash
./scripts/talos-local.sh up
```

Destroy the rehearsal cluster when done:

```bash
./scripts/talos-local.sh down
```
