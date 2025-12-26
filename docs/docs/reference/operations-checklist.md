---
sidebar_position: 2
title: Operations Checklist
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
