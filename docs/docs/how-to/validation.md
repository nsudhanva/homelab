---
sidebar_position: 2
title: Validation
---

# Validation

## Step 1: Validate the cluster

```bash
kubectl get nodes
kubectl get pods -A
```

## Step 2: Validate GitOps sync

```bash
kubectl get apps -n argocd
```

## Step 3: Run local checks before push

```bash
pre-commit run --all-files
kubectl get nodes
kubectl get pods -A
```
