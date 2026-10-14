---
title: Connect Git Repository to ArgoCD
description: Add a Git repository to ArgoCD for GitOps deployments. Configure repository access with the CLI or the UI, and make sure that ApplicationSets can sync.
keywords:
  - argocd add repository
  - argocd repo connection
  - argocd git repository
  - argocd login cli
  - argocd repository credentials
sidebar:
  order: 5
---

# Connect This Repo To ArgoCD

This guide connects `https://github.com/nsudhanva/homelab` to ArgoCD. Then the ApplicationSets can sync from Git.

## Step 1: Get the initial admin password

Get the bootstrap password from the `argocd-initial-admin-secret` Secret:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo
```

## Step 2: Sign in to ArgoCD

Use the CLI or the UI. If you are on the tailnet, the UI is at `https://argocd.sudhanva.me`.

### CLI

```bash
argocd login argocd.sudhanva.me \
  --username admin \
  --password "<INITIAL_PASSWORD>" \
  --grpc-web
```

If the CLI cannot resolve `argocd.sudhanva.me`, make sure that split DNS is configured. Also make sure that you can reach the tailnet resolver:

```bash
dig +short argocd.sudhanva.me @100.100.100.100
```

If the query times out or returns no records, follow the [Tailscale](./tailscale.md) guide.

## Step 3: Add the repository

The repository is public. Thus, HTTPS is enough.

### CLI

```bash
argocd repo add https://github.com/nsudhanva/homelab.git
```

### UI

Open ArgoCD. Go to Settings, then Repositories, then Connect Repo. Use the HTTPS URL.

## Step 4: Make sure that ArgoCD can see the repository

```bash
argocd repo list
```

The output shows `https://github.com/nsudhanva/homelab.git` as a repository.
