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

This guide tells how to do routine maintenance on bare-metal nodes. It includes operating system patches, automatic K3s upgrades, and volume backups.

## Routine Cluster Health Checks

Examine the health of the cluster nodes, the pods, and the GitOps sync state:

```bash
kubectl get nodes -o wide
kubectl get pods -A
kubectl get applications -n argocd
```

Make sure that the local storage path `/home/k3s-storage` has enough free disk space:

```bash
ssh sudhanva@100.66.139.118 "df -h /home/k3s-storage"
```

## Node Maintenance and OS Patching

Before you update the host operating system (Ubuntu 26.04 LTS) or apply kernel updates, drain the workloads. Then reboot the node.

### Step 1: Cordon the node

Mark the node as unschedulable. This stops the scheduler from putting new pods on the node:

```bash
kubectl cordon legion
```

### Step 2: Drain active workloads

Evict the running pods. The drain command respects DaemonSets and local data volumes:

```bash
kubectl drain legion --ignore-daemonsets --delete-emptydir-data --force
```

### Step 3: Apply host updates and reboot

Log in to the host machine. Update the packages and reboot the node:

```bash
ssh sudhanva@100.66.139.118
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### Step 4: Uncordon the node

When the node starts and shows `Ready`, uncordon it. The scheduler can then put pods on the node again:

```bash
kubectl uncordon legion
```

Make sure that all workloads in `media`, `argocd`, `vault`, and `monitoring` go back to the `Running` state:

```bash
kubectl get pods -A
```

## Automated K3s Upgrades with System Upgrade Controller

The cluster uses Rancher System Upgrade Controller (`infrastructure/system-upgrade-controller/`) to upgrade K3s automatically with no downtime.

### Step 1: Update the upgrade plan

Open `infrastructure/system-upgrade-controller/k3s-upgrade-plan.yaml`. Change the target K3s version tag in `spec.version`:

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

Commit the manifest change. Push it to master:

```bash
git add infrastructure/system-upgrade-controller/k3s-upgrade-plan.yaml
git commit -m "chore: bump k3s upgrade plan to v1.36.5+k3s1"
git push origin master
```

### Step 3: Monitor the upgrade job

ArgoCD syncs the updated Plan. The System Upgrade Controller then deploys a privileged upgrade job. This job drains the node and installs the specified K3s binary. It then restarts the service and uncordons the node. Monitor the job:

```bash
kubectl get pods -n system-upgrade -w
kubectl get nodes
```

## Storage and Application Backups

The native Local-Path Provisioner keeps all persistent storage on `/home/k3s-storage`. Thus, disaster recovery is easy.

### Local-Path Volume Backups

Make snapshot backups of the application data directories in `/home/k3s-storage/`:

```bash
ssh sudhanva@100.66.139.118 "sudo tar -czvf /home/k3s-storage-backup-$(date +%F).tar.gz /home/k3s-storage"
```

### Vault Unseal Keys

Keep the five Shamir unseal keys and the root token from `vault-keys.json` in an offline password manager. If Kubernetes reschedules the Vault pod or the pod restarts, unseal Vault:

```bash
kubectl -n vault exec -it vault-0 -- vault operator unseal <key>
```
