---
sidebar_position: 1
title: Deploy Apps With GitOps
---

# Deploy Apps With GitOps

This guide shows how to use this repo to deploy new workloads through ArgoCD ApplicationSets.

## Step 1: Add a new app directory

Create a folder under `apps/` and include an `app.yaml` file to define the ArgoCD application settings, plus separate YAML files for each resource.

Example layout:

- `apps/my-app/namespace.yaml`
- `apps/my-app/app.yaml`
- `apps/my-app/deployment.yaml`
- `apps/my-app/service.yaml`
- `apps/my-app/ingress.yaml`

`app.yaml` defines the app name, path, and namespace. Example:

```yaml
name: my-app
path: apps/my-app
namespace: my-app
```

ArgoCD will create an application named `app-my-app` from this folder and sync it to the namespace defined in `app.yaml`.

## Step 2: Use Tailscale ingress for HTTPS

When exposing HTTPS, use `ingressClassName: tailscale` and the Tailscale annotations used elsewhere in `infrastructure/`.

## Step 3: Commit and push

ArgoCD watches the repo and applies changes via ApplicationSets. Once your changes are pushed, ArgoCD will sync the new app.

:::note

If your app needs to share data with another app, place them in the same namespace (by pointing both `app.yaml` files at the same namespace) or use an RWX volume that is intentionally shared. Avoid cross-namespace PVC references.

:::

## Step 4: Verify in ArgoCD

```bash
kubectl get apps -n argocd
```

## Step 5: Trigger a manual sync

Use this if the app is out of sync or if auto-sync is disabled.

:::note

If auto-sync is enabled on the ApplicationSet, ArgoCD will reconcile automatically after your push.

:::

### Option A: Sync in the UI

Open the ArgoCD UI, select the application, then click Sync.

### Option B: Sync with CLI

```bash
argocd app sync <app-name>
argocd app wait <app-name> --health
```
