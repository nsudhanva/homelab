---
title: K3s Cluster Maintenance and Upgrades
description: Routine maintenance procedures for the bare-metal K3s cluster including OS patching, node draining, automated K3s upgrades via System Upgrade Controller, and storage backups.
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

This guide covers routine maintenance, operating system patching, automated K3s upgrades, and volume backup procedures for bare-metal nodes.

## Routine Cluster Health Checks

Perform routine health checks across cluster nodes, pods, and GitOps sync state:

```bash
kubectl get nodes -o wide
kubectl get pods -A
kubectl get applications -n argocd
```

Confirm that the local storage path `/home/k3s-storage` has ample free disk space:

```bash
ssh sudhanva@100.66.139.118 "df -h /home/k3s-storage"
```

## Node Maintenance and OS Patching

When updating the host operating system (Ubuntu 26.04 LTS) or applying kernel updates, drain workloads cleanly before rebooting.

### Step 1: Cordon the node

Mark the node as unschedulable to prevent new pods from being assigned:

```bash
kubectl cordon legion
```

### Step 2: Drain active workloads

Evict running pods gracefully while honoring DaemonSets and local data volumes:

```bash
kubectl drain legion --ignore-daemonsets --delete-emptydir-data --force
```

### Step 3: Apply host updates and reboot

Log in to the host machine, run package updates, and reboot the node:

```bash
ssh sudhanva@100.66.139.118
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### Step 4: Uncordon the node

After the node boots up and reports `Ready`, uncordon it to resume scheduling:

```bash
kubectl uncordon legion
```

Verify that all workloads in `media`, `argocd`, `vault`, and `monitoring` return to `Running` state:

```bash
kubectl get pods -A
```

## Automated K3s Upgrades with System Upgrade Controller

The cluster utilizes Rancher System Upgrade Controller (`infrastructure/system-upgrade-controller/`) to execute automated, zero-downtime upgrades of K3s.

### Step 1: Update the upgrade plan

Open `infrastructure/system-upgrade-controller/k3s-upgrade-plan.yaml` and update the target K3s version tag in `spec.version`:

```yaml
apiVersion: upgrade.cattle.io/v1
kind: Plan
metadata:
  name: k3s-server
  namespace: system-upgrade
spec:
  concurrency: 1
  nodeSelector:
    matchExpressions:
      - key: node.homelab/role
        operator: In
        values:
          - controlplane
  serviceAccountName: system-upgrade
  cordon: true
  drain:
    force: true
    ignoreDaemonSets: true
    deleteEmptydirData: true
  version: "v1.36.5+k3s1"
```

### Step 2: Commit and push changes

Commit the manifest change and push to master:

```bash
git add infrastructure/system-upgrade-controller/k3s-upgrade-plan.yaml
git commit -m "chore: bump k3s upgrade plan to v1.36.5+k3s1"
git push origin master
```

### Step 3: Monitor the upgrade job

ArgoCD syncs the updated Plan. The System Upgrade Controller deploys a privileged upgrade job that drains the node, installs the specified K3s binary, restarts the service, and uncordons the node:

```bash
kubectl get pods -n system-upgrade -w
kubectl get nodes
```

## Storage and Application Backups

Because all persistent storage is backed by the native Local-Path Provisioner on `/home/k3s-storage`, disaster recovery is straightforward.

### Local-Path Volume Backups

Create snapshot backups of application data directories located at `/home/k3s-storage/`:

```bash
ssh sudhanva@100.66.139.118 "sudo tar -czvf /home/k3s-storage-backup-$(date +%F).tar.gz /home/k3s-storage"
```

### Vault Unseal Keys

Ensure your five Shamir unseal keys and root token in `vault-keys.json` are securely preserved in an offline password manager. If the Vault pod is rescheduled or restarted, unseal Vault using:

```bash
kubectl -n vault exec -it vault-0 -- vault operator unseal <key>
```
