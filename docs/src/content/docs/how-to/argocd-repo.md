---
title: Connect This Repo To ArgoCD
---

# Connect This Repo To ArgoCD

This guide connects `https://github.com/nsudhanva/homelab` to ArgoCD so ApplicationSets can sync from Git.

## Step 1: Get the initial admin password

Fetch the bootstrap password from the `argocd-initial-admin-secret` Secret:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo
```

## Step 2: Sign in to ArgoCD

Use the CLI or UI. If you are on the tailnet, the UI is at `https://argocd.sudhanva.me`.

### CLI

```bash
argocd login argocd.sudhanva.me \
  --username admin \
  --password "<INITIAL_PASSWORD>" \
  --grpc-web
```

If the CLI cannot resolve `argocd.sudhanva.me`, verify split DNS is configured and the tailnet resolver is reachable:

```bash
dig +short argocd.sudhanva.me @100.100.100.100
```

Follow [Tailscale](./tailscale.md) if the query times out or returns no records.

## Step 3: Add the repository

The repo is public, so HTTPS is enough.

### CLI

```bash
argocd repo add https://github.com/nsudhanva/homelab.git
```

### UI

Open ArgoCD, go to Settings, then Repositories, then Connect Repo. Use the HTTPS URL.

## Step 4: Verify ArgoCD can see the repo

```bash
argocd repo list
```

You should see `https://github.com/nsudhanva/homelab.git` listed as a repository.
