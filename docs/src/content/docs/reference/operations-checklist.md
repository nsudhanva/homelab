---
title: Operations Checklist Reference
description: Checklists for routine Kubernetes cluster operations. They include health checks, checks before a push, and checks after a reboot.
keywords:
  - kubernetes operations
  - kubectl commands
  - cluster health check
  - kubernetes checklist
  - argocd status check
  - kubernetes maintenance commands
sidebar:
  order: 4
---

# Operations Checklist

Use these checklists for clusters that run for a long time.

## Routine checks

```bash
kubectl get nodes
kubectl get pods -A
kubectl get apps -n argocd
```

## Before pushing changes

```bash
pre-commit run --all-files
kubectl get nodes
kubectl get pods -A
kubectl get applications -n argocd
```

## After a node reboot

Vault starts sealed after every restart. Check its status, and unseal it if `Sealed` is `true`. Refer to [Vault Unseal Keys](/how-to/maintenance/#vault-unseal-keys).

```bash
kubectl get nodes
kubectl -n vault exec vault-0 -- vault status
kubectl get pods -A
kubectl get externalsecrets -A
```
