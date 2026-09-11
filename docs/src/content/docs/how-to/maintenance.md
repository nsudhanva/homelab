---
title: Talos Cluster Maintenance and Upgrades
description: Perform routine Talos cluster maintenance including node upgrades, Kubernetes upgrades, and component updates through GitOps for immutable infrastructure.
keywords:
  - talos maintenance
  - talos upgrade
  - kubernetes version upgrade
  - node drain kubernetes
  - cilium upgrade
  - argocd upgrade
  - longhorn upgrade
  - talos node maintenance
sidebar:
  order: 13
---

# Maintenance

:::note

These steps target hardware clusters. For local rehearsal testing, use [Local Talos Cluster](../tutorials/local-talos-cluster.md).

:::

## Adding Nodes to the Cluster

This section covers expanding the cluster with additional worker nodes or control plane nodes.

### Add a Worker Node

Add the machine to `workers` in `talos/nodes.yaml`, boot it into maintenance mode, and apply its configuration:

```bash
./scripts/talos-baremetal.sh gen-config
./scripts/talos-baremetal.sh apply --role worker --limit <worker-hostname>
```

### Add a Control Plane Node (HA Setup)

Add the machine to `controlplanes` in `talos/nodes.yaml` and make sure the control plane endpoint in the same file points at the shared address clients use. Then render and apply:

```bash
./scripts/talos-baremetal.sh gen-config
./scripts/talos-baremetal.sh apply --role controlplane --limit <new-hostname>
```

The new control plane joins etcd with the shared secrets bundle. No certificate keys are copied by hand.

## Routine checks

Use these checks if the cluster runs unattended for long periods.

```bash
kubectl get nodes
kubectl get pods -A
kubectl get apps -n argocd
```

## Namespace migration

Use this flow to move existing apps out of the `default` namespace.

### Step 1: Add a namespace and update manifests

Create `apps/<app-name>/namespace.yaml` and `apps/<app-name>/app.yaml`, then update every manifest in the app folder to use `namespace: <app-name>`. If two apps must share storage, point both `app.yaml` files at the same namespace.

### Step 2: Let ArgoCD sync

Once the changes are pushed, ArgoCD will reconcile the app into the new namespace.

### Step 3: Remove old resources

After the new namespace is healthy, delete the old resources in `default` to avoid conflicts.

```bash
kubectl delete deployment,service,httproute -n default -l app=<app-name>
```

If the app owns PVCs, plan a data migration before deleting the old claims.

## Node maintenance window

Use this flow to reboot a node safely.

### Step 1: Drain the node

```bash
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

### Step 2: Reboot the node

```bash
talosctl -n <node-ip> reboot
```

Confirm the node is back online and Ready before continuing.

### Step 3: Uncordon the node

```bash
kubectl uncordon <node-name>
```

## Upgrade Talos Linux

Bump the Talos version in `talos/versions.yaml`, then roll the upgrade across the cluster:

```bash
./scripts/talos-baremetal.sh upgrade-talos
```

The script upgrades control planes one at a time, then workers, waiting for health between nodes.

## Upgrade Kubernetes

Bump the Kubernetes version in `talos/versions.yaml`, then roll the upgrade:

```bash
./scripts/talos-baremetal.sh upgrade-k8s
```

### Verify the upgrade

```bash
kubectl get nodes
kubectl get pods -A
```

## Version Management (Talos + ArgoCD)

Use this flow to keep every layer consistent.

### Pinned versions

Node-level versions are pinned in `talos/versions.yaml`:

- `talos` for the immutable OS image
- `kubernetes` for the control plane components
- `cilium` for the CNI chart used by ArgoCD

Cluster-level components (Longhorn, Tailscale, Envoy Gateway, cert-manager, ExternalDNS, ArgoCD) are pinned in their ArgoCD manifests:

- `bootstrap/templates/longhorn.yaml`
- `infrastructure/tailscale/tailscale-operator.yaml`
- `infrastructure/envoy-gateway/envoy-gateway.yaml`
- `infrastructure/envoy-gateway-crds/`
- `infrastructure/gateway-api-crds/`
- `infrastructure/cert-manager/cert-manager.yaml`
- `infrastructure/external-dns/external-dns.yaml`
- `infrastructure/external-secrets-crds/`
- `bootstrap/templates/*-appset.yaml` for repo references

### Apply the change consistently

- **Node and Kubernetes versions**: bump `talos/versions.yaml` and run the upgrade script so every node converges to the same version.
- **Cluster add-ons** (Cilium, Longhorn, ArgoCD): update the version in Git and let ArgoCD sync.

### Keep HA during updates

- Upgrade control planes one at a time, then workers.
- Drain nodes before disruptive operations and uncordon after.
- Verify health between nodes: `kubectl get nodes` and `kubectl get pods -A`.

## Upgrade Cilium

Update the `cilium` pin in `talos/versions.yaml` and `targetRevision` in `infrastructure/cilium/cilium.yaml`, then push and let ArgoCD roll the DaemonSet.

## Upgrade ArgoCD

Update `bootstrap/argocd/kustomization.yaml` to the desired ArgoCD release tag.

```bash
kubectl apply -k bootstrap/argocd
kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd
```

## Upgrade Longhorn

Update `targetRevision` in `bootstrap/templates/longhorn.yaml`, then let ArgoCD sync the application.

:::warning

Longhorn enforces consecutive minor upgrades. Step one minor at a time (for example 1.11.x to 1.12.x). Skipping minors fails the pre-upgrade check and blocks the sync while leaving the running version intact.

:::

## Recreate From Scratch

Use this section when rebuilding a node from blank hardware:

Flash the installer USB from [Boot Media](../tutorials/system-prep.md), boot the machine into maintenance mode, and apply its configuration:

```bash
./scripts/talos-baremetal.sh gen-config
./scripts/talos-baremetal.sh apply --limit <hostname>
```

Then continue at [Talos Bootstrap](../tutorials/kubernetes.md).

If you are rebuilding with existing data disks for Longhorn, ensure the storage path in `bootstrap/templates/longhorn.yaml` points to the correct mount before applying `bootstrap/root.yaml`.
