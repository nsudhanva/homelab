---
title: Operations Checklist Reference
description: Quick reference checklists for routine Kubernetes cluster operations including health checks, pre-push validation, and post-reboot verification commands.
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

Use these checklists for long-running clusters.

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
```

## After a node reboot

```bash
kubectl get nodes
kubectl get pods -A
```
