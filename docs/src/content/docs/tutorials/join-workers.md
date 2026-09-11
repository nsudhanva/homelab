---
title: Add Worker Nodes to Talos Cluster
description: Add Talos Linux worker machines to an existing cluster by extending the inventory, rendering worker configuration, and applying it over the Talos API.
keywords:
  - talos worker node
  - add node to cluster
  - talos apply-config
  - kubernetes cluster expansion
  - multi-node talos
sidebar:
  order: 8
---

# Add Workers

Use this after the control plane is bootstrapped to add worker machines to the cluster. If you are adding brand new hardware, start with [Add a Worker Node](../how-to/add-worker-node.md).

## Step 1: Render the worker configuration

Workers share the cluster secrets and the common patches, plus the worker role patch:

```bash
./scripts/talos-baremetal.sh gen-config
```

## Step 2: Apply configuration to each worker

Push the rendered worker file to machines waiting in maintenance mode:

```bash
./scripts/talos-baremetal.sh apply --role worker
```

Workers install Talos, reboot, and join the cluster with the shared PKI. No join tokens are created or copied by hand.

## Step 3: Verify the nodes

```bash
kubectl get nodes -o wide
```
