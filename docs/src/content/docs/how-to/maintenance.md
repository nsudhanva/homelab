---
title: K3s Cluster Maintenance and Upgrades
description: Maintenance procedures for the bare-metal K3s cluster. Patch the OS, drain the node, upgrade K3s with System Upgrade Controller, and back up storage.
keywords:
  - k3s cluster maintenance
  - k3s version upgrade
  - node drain kubernetes
  - system upgrade controller
  - ubuntu server maintenance
  - local storage backup
sidebar:
  order: 13
---

# Cluster Maintenance

This guide gives the routine maintenance procedures for the bare-metal node. It includes operating system patches, K3s upgrades, and volume backups.

## Routine Cluster Health Checks

Examine the health of the cluster nodes, the pods, and the GitOps sync state:

```bash
kubectl get nodes -o wide
kubectl get pods -A
kubectl get applications -n argocd
```

Make sure that the local storage path `/home/k3s-storage` has sufficient free disk space:

```bash
ssh sudhanva@100.66.139.118 "df -h /home/k3s-storage"
```

## Node Maintenance and OS Patching

Drain the workloads before you update the host operating system (Ubuntu 26.04 LTS) or apply kernel updates. Then reboot the node.

### Step 1: Cordon the node

Mark the node as unschedulable. The scheduler then puts no new pods on the node.

```bash
kubectl cordon legion
```

### Step 2: Drain active workloads

Evict the running pods. The drain command skips DaemonSet pods and deletes `emptyDir` data.

```bash
kubectl drain legion --ignore-daemonsets --delete-emptydir-data --force
```

### Step 3: Apply host updates and reboot

Log in to the host machine. Update the packages and reboot the node.

```bash
ssh sudhanva@100.66.139.118
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### Step 4: Uncordon the node

When the node shows `Ready`, uncordon it. The scheduler can then put pods on the node again.

```bash
kubectl uncordon legion
```

Unseal Vault. Refer to [Vault Unseal Keys](#vault-unseal-keys). Then make sure that all workloads in `media`, `argocd`, `vault`, and `monitoring` are in the `Running` state:

```bash
kubectl get pods -A
```

## Automated K3s Upgrades with System Upgrade Controller

Rancher System Upgrade Controller `v0.20.2` in `infrastructure/system-upgrade-controller/` upgrades K3s from Git. The `kustomization.yaml` file pulls the upstream release manifests and adds `k3s-upgrade-plan.yaml`.

### Step 1: Update the upgrade plan

Open `infrastructure/system-upgrade-controller/k3s-upgrade-plan.yaml`. Change the target K3s version in `spec.version`. This is the Plan in the repository:

```yaml
apiVersion: upgrade.cattle.io/v1
kind: Plan
metadata:
  name: k3s-server
  namespace: system-upgrade
spec:
  concurrency: 1
  version: v1.37.1+k3s1
  nodeSelector:
    matchExpressions:
      - key: node-role.kubernetes.io/control-plane
        operator: Exists
  serviceAccountName: system-upgrade
  tolerations:
    - key: CriticalAddonsOnly
      operator: Exists
    - key: node-role.kubernetes.io/control-plane
      operator: Exists
      effect: NoSchedule
  cordon: false
  upgrade:
    image: rancher/k3s-upgrade
```

The Plan sets `cordon: false` and has no `drain` block. The controller does not cordon or drain the node. Pods continue to run while the K3s binary changes and the `k3s` service restarts.

Set `k3s_version` in `ansible/group_vars/all.yaml` to the same value. Ansible uses this value only when it installs K3s on a host that does not have K3s.

### Step 2: Commit and push changes

Commit the manifest change. Push it to `master`.

```bash
git add infrastructure/system-upgrade-controller/k3s-upgrade-plan.yaml ansible/group_vars/all.yaml
git commit -m "chore: bump k3s to <version>"
git push origin master
```

### Step 3: Monitor the upgrade job

ArgoCD syncs the updated Plan. The System Upgrade Controller then starts a privileged upgrade Job on each node with the `node-role.kubernetes.io/control-plane` label. The Job runs `rancher/k3s-upgrade`, which replaces the K3s binary and restarts the service. Monitor the Job:

```bash
kubectl get plans -n system-upgrade
kubectl get pods -n system-upgrade -w
kubectl get nodes
```

## Storage and Application Backups

The K3s Local-Path Provisioner keeps all persistent storage in `/home/k3s-storage`. A backup of this directory contains all volumes.

### Local-Path Volume Backups

Make a snapshot backup of the application data directories in `/home/k3s-storage/`:

```bash
ssh sudhanva@100.66.139.118 "sudo tar -czvf /home/k3s-storage-backup-$(date +%F).tar.gz /home/k3s-storage"
```

### Vault Unseal Keys

Keep the unseal keys and the root token from `vault operator init` in an offline password manager. Vault uses file storage with no auto-unseal, so it starts sealed after every pod restart. Unseal it with three of the five keys:

```bash
kubectl -n vault exec -it vault-0 -- vault operator unseal <key>
```
