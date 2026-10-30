---
title: Sync and Manage ArgoCD Applications
description: Refresh, sync, and repair drift in ArgoCD applications, and sync all Applications of one ApplicationSet.
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

Use this guide to refresh the status of an application, start a sync, or repair drift. The `apps` and `infrastructure` ApplicationSets enable automated sync on each Application. Use a manual sync during troubleshooting.

## Step 1: Check application status

```bash
kubectl get apps -n argocd
```

## Step 2: Refresh app status

```bash
argocd app get <app-name> --refresh
```

:::note

If you do not have the ArgoCD CLI, use the ArgoCD UI to refresh and sync.

:::

## Step 3: Trigger a sync

```bash
argocd app sync <app-name>
argocd app wait <app-name> --health
```

## Step 4: Sync all apps from one ApplicationSet

The ApplicationSets set no labels on their Applications, so select the Applications by name prefix. The `apps` ApplicationSet names its Applications `app-<name>`. The `infrastructure` ApplicationSet names its Applications `infra-<directory>`.

```bash
argocd app list -o name | grep '/app-' | xargs -n1 argocd app sync
argocd app list -o name | grep '/infra-' | xargs -n1 argocd app sync
```

## Step 5: Reconcile drift

If an application continues to drift, examine the diff. Then repair the source manifest in Git.

```bash
argocd app diff <app-name>
```
