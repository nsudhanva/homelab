---
title: Add Worker Node to Talos Cluster
description: Add a new Talos Linux worker machine to an existing cluster. Covers inventory, machine configuration, GPU workers, and Longhorn storage labels.
keywords:
  - add talos worker node
  - talos cluster scaling
  - gpu worker node
  - longhorn node label
  - talos worker configuration
sidebar:
  order: 2
---

# Add a Worker Node

Use this guide when you want to add a worker to an existing control plane without rebuilding the cluster.

## Step 1: Update the machine inventory

Add the new machine under `workers` in `talos/nodes.yaml` with its hostname, LAN IP, and install disk. For GPU workers, note the GPU type alongside the entry so the follow-up steps apply.

## Step 2: Confirm shared settings

Check the pinned versions in `talos/versions.yaml` and the role patches in `talos/patches/worker.yaml`. Worker machines receive the `node.homelab/role=worker` label for workload placement.

If you change the Longhorn storage layout, also update the Longhorn bootstrap template in `bootstrap/templates/longhorn.yaml`.

## Step 3: Boot the machine into maintenance mode

Flash the installer USB from [Boot Media](../tutorials/system-prep.md) and boot the new machine. It waits for configuration over the Talos API.

## Step 4: Render and apply the worker configuration

```bash
./scripts/talos-baremetal.sh gen-config
./scripts/talos-baremetal.sh apply --role worker --limit <worker-hostname>
```

The worker installs Talos, reboots, and joins the cluster with the shared PKI.

## Step 5: Enable Longhorn disk creation on the node

If Longhorn is in use, label the node so it gets a default disk:

```bash
kubectl label node <worker-node-name> node.longhorn.io/create-default-disk=true --overwrite
```

## Step 6: Validate the node

```bash
kubectl get nodes -o wide
```

If the node stays `NotReady`, verify the Cilium agents are healthy in `kube-system` and that the worker can reach the API server endpoint.
