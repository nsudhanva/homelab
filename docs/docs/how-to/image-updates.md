---
title: Automated Image Updates
---

# Automated Image Updates

This guide enables ArgoCD Image Updater to track container images and commit updates back to Git.

## Step One: Store registry credentials in Vault

Create these Vault secrets:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd-image-updater/ghcr \
  username="REPLACE_ME" token="REPLACE_ME"

kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd-image-updater/dockerhub \
  username="REPLACE_ME" token="REPLACE_ME"
```

## Step Two: Store Git write-back credentials in Vault

Create a GitHub token with repo write access and store it:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd/repo-creds \
  username="REPLACE_ME" token="REPLACE_ME"
```

## Step Three: Let ArgoCD sync

ArgoCD will install ArgoCD Image Updater, create the registry secret, and create the repo credentials.

## Step Four: Verify image updates

Look for `.argocd-source-<appName>.yaml` files added under `apps/` after Image Updater runs.

## Notes

- Image rules live in `infrastructure/argocd-image-updater/image-updater.yaml`.
- Registry secrets are created by External Secrets in `infrastructure/external-secrets/`.
- Updates commit to the tracked branch (`master`) so ArgoCD can auto-sync.
- Apps should include a `kustomization.yaml` so ArgoCD can apply Image Updater overrides.
