---
sidebar_position: 9
title: Connect This Repo To ArgoCD
---

# Connect This Repo To ArgoCD

This guide connects `https://github.com/nsudhanva/homelab` to ArgoCD so ApplicationSets can sync from Git.

## Step 1: Sign in to ArgoCD

Use the CLI or UI. If you are on the tailnet, the UI is at `https://argocd.sudhanva.me`.

### CLI

```bash
argocd login argocd.sudhanva.me
```

## Step 2: Add the repository

The repo is public, so HTTPS is enough.

### CLI

```bash
argocd repo add https://github.com/nsudhanva/homelab.git
```

### UI

Open ArgoCD, go to Settings, then Repositories, then Connect Repo. Use the HTTPS URL.

## Step 3: Verify ArgoCD can see the repo

```bash
argocd repo list
```

You should see `https://github.com/nsudhanva/homelab.git` listed as a repository.
