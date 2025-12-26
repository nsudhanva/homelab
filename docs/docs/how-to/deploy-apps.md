---
sidebar_position: 1
title: Deploy Apps With GitOps
---

# Deploy Apps With GitOps

This guide shows how to use this repo to deploy new workloads through ArgoCD ApplicationSets.

## Step 1: Add a new app directory

Create a folder under `apps/` and include separate YAML files for each resource.

Example layout:

- `apps/my-app/deployment.yaml`
- `apps/my-app/service.yaml`
- `apps/my-app/ingress.yaml`

ArgoCD will create an application named `app-my-app` from this folder.

## Step 2: Use Tailscale ingress for HTTPS

When exposing HTTPS, use `ingressClassName: tailscale` and the Tailscale annotations used elsewhere in `infrastructure/`.

## Step 3: Commit and push

ArgoCD watches the repo and applies changes via ApplicationSets. Once your changes are pushed, ArgoCD will sync the new app.

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
