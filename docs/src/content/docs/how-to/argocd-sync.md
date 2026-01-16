---
title: Sync and Manage ArgoCD Applications
description: Force sync, refresh status, and recover from drift in ArgoCD applications. Manage ApplicationSets and troubleshoot sync issues.
keywords:
  - argocd sync
  - argocd refresh
  - argocd drift
  - argocd applicationset sync
  - argocd troubleshooting
  - argocd cli commands
sidebar:
  order: 4
---

# Sync ArgoCD Applications

Use this guide to force a sync, refresh status, or recover from drift. Auto-sync is enabled by default in the ApplicationSets, but manual sync is useful for troubleshooting.

## Step 1: Check application status

```bash
kubectl get apps -n argocd
```

## Step 2: Refresh app status

```bash
argocd app get <app-name> --refresh
```

:::note

If you do not have the ArgoCD CLI, use the UI to refresh and sync.

:::

## Step 3: Trigger a sync

```bash
argocd app sync <app-name>
argocd app wait <app-name> --health
```

## Step 4: Sync an entire ApplicationSet

```bash
argocd app sync -l app.kubernetes.io/instance=apps
argocd app sync -l app.kubernetes.io/instance=infrastructure
```

## Step 5: Reconcile drift

If the app keeps drifting, inspect the diff and fix the source manifest in Git.

```bash
argocd app diff <app-name>
```
