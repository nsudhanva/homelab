---
title: Talos Machine Configuration
description: Render declarative Talos machine configuration from the repo inventory and patches. Covers secrets generation, CNI and proxy settings for Cilium, and per-role patches.
keywords:
  - talos machine configuration
  - talos config patch
  - talos secrets
  - talos cilium cni
  - talos disable kube-proxy
  - infrastructure as code talos
sidebar:
  order: 4
---

# Machine Configuration

Every Talos machine is configured from version-controlled files. Nothing is typed into a machine by hand.

## Step 1: Learn the layout

- `talos/nodes.yaml` lists control planes and workers with hostnames, IPs, and install disks
- `talos/versions.yaml` pins Talos and Kubernetes versions
- `talos/patches/common.yaml` disables the built-in CNI and kube-proxy so Cilium owns networking
- `talos/patches/controlplane.yaml` allows scheduling on control planes for compact clusters
- `talos/patches/worker.yaml` labels worker nodes for workload placement

## Step 2: Generate secrets once

```bash
./scripts/talos-baremetal.sh gen-secrets
```

Secrets are generated a single time and reused for every machine. The script keeps them out of Git and reuses the stored copy on later runs.

## Step 3: Render machine configs

```bash
./scripts/talos-baremetal.sh gen-config
```

The script renders one configuration file per machine into `talos/_out/`. Review the rendered output before applying and confirm the CNI and proxy settings plus the endpoint match `talos/nodes.yaml`.

## Step 4: Apply and install

```bash
./scripts/talos-baremetal.sh apply
```

Each machine in maintenance mode receives its configuration and installs Talos to its install disk. Continue with [Talos Bootstrap](./kubernetes.md) once every machine reports healthy over the API.
