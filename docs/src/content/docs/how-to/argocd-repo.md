---
title: Connect Git Repository to ArgoCD
description: How ArgoCD gets access to this Git repository. An ExternalSecret creates the repository Secret from Vault, and the ApplicationSets sync from it.
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

ArgoCD reads `https://github.com/nsudhanva/homelab.git`. The repository is public, so ArgoCD can clone it without credentials. ArgoCD Image Updater needs credentials to push its write-back commits, so the repo declares a repository Secret. Do not add the repository with `argocd repo add` or the UI. External Secrets manages it.

## Step 1: Store the GitHub credentials in Vault

Create a GitHub personal access token with write access to the repository. Store it in Vault:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd/repo-creds \
  username="REPLACE_ME" token="REPLACE_ME"
```

## Step 2: Let ArgoCD sync the ExternalSecret

`infrastructure/external-secrets/external-secret-argocd-repo-creds.yaml` defines the ExternalSecret `repo-homelab` in the `argocd` namespace. It reads `kv/argocd/repo-creds` (properties `username` and `token`) and creates the Secret `repo-homelab` with these values:

- Label `argocd.argoproj.io/secret-type: repository`
- `type: git`
- `url: https://github.com/nsudhanva/homelab.git`
- `username` and `password` from Vault

ArgoCD finds repository Secrets by that label. ArgoCD syncs the ExternalSecret as part of `infra-external-secrets`.

## Step 3: Make sure that ArgoCD sees the repository

Examine the ExternalSecret and the Secret:

```bash
kubectl -n argocd get externalsecret repo-homelab
kubectl -n argocd get secret repo-homelab -o jsonpath='{.metadata.labels}'; echo
```

If you have the ArgoCD CLI, sign in and list the repositories. Get the initial admin password from the `argocd-initial-admin-secret` Secret:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo
```

```bash
argocd login argocd.sudhanva.me --username admin --grpc-web
argocd repo list
```

The output shows `https://github.com/nsudhanva/homelab.git`.

If the CLI cannot resolve `argocd.sudhanva.me`, make sure that split DNS is configured and that you can reach the tailnet resolver:

```bash
dig +short argocd.sudhanva.me @100.100.100.100
```

If the query times out or returns no records, follow the [Tailscale](/how-to/tailscale/) guide.
