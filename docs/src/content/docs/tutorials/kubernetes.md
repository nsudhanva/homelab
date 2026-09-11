---
title: Bootstrap the Talos Cluster
description: Apply machine configuration to Talos nodes, bootstrap etcd, fetch kubeconfig, and verify the Kubernetes API on Talos Linux v1.14 with Kubernetes v1.37.
keywords:
  - talos bootstrap
  - talos apply-config
  - talos etcd bootstrap
  - talos kubeconfig
  - talos maintenance mode
  - bare metal kubernetes cluster
sidebar:
  order: 5
---

# Talos Bootstrap

Bootstrapping turns configured Talos machines into a Kubernetes cluster. The whole flow runs from the workstation through the Talos API.

## Step 1: Apply machine configuration

Every machine boots its installer image into maintenance mode first. Push each rendered configuration from `talos/_out/`:

```bash
./scripts/talos-baremetal.sh apply
```

Machines install Talos to their install disks and reboot into the configured system. Wait until every machine answers over the API:

```bash
talosctl -n <machine-ip> get members
```

## Step 2: Bootstrap etcd

Bootstrap once against the first control plane:

```bash
./scripts/talos-baremetal.sh bootstrap
```

Etcd forms, the Kubernetes control plane components start, and worker nodes join with the PKI from the shared secrets bundle.

## Step 3: Fetch kubeconfig

```bash
./scripts/talos-baremetal.sh kubeconfig
export KUBECONFIG=$PWD/talos/_out/kubeconfig
kubectl get nodes -o wide
```

Nodes report Ready once Cilium is deployed by ArgoCD in [ArgoCD and GitOps](./argocd.md). Pods stay pending until the CNI arrives, which is expected on a fresh bootstrap.

## Step 4: Confirm API OIDC for Headlamp

If Headlamp should offer OIDC logins, set the API server OIDC arguments before the first bootstrap by extending the control plane patch with an API server configuration document. Apply the change with `./scripts/talos-baremetal.sh apply` and the API server rolls with the new flags. See [Headlamp](../how-to/headlamp.md) for the Vault provider values.

## Step 5: Add workers later

Follow [Add Workers](./join-workers.md) after the control plane is healthy.
