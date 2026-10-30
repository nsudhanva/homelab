---
title: Operations Checklist Reference
description: Checklists for routine cluster operations, which include health checks, checks before a push, and checks after a reboot.
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

Use these checklists to monitor the cluster and to examine it after a change or a reboot.

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

Vault starts sealed after each restart. Examine the Vault status. If `Sealed` is `true`, unseal Vault. Refer to [Vault Unseal Keys](/how-to/maintenance/#vault-unseal-keys).

```bash
kubectl get nodes
kubectl -n vault exec vault-0 -- vault status
kubectl get pods -A
kubectl get externalsecrets -A
```
