---
title: Automated Container Image Updates with ArgoCD
description: Configure ArgoCD Image Updater to track container image versions and commit the updates to Git for GitOps deployments.
keywords:
  - argocd image updater
  - automated image updates
  - container image versioning
  - gitops image automation
  - ghcr credentials
  - dockerhub credentials
  - kustomization image override
sidebar:
  order: 6
---

# Automated Image Updates

This guide configures ArgoCD Image Updater. Image Updater tracks container images and commits the updates to Git.

## Step 1: Store registry credentials in Vault

Create these Vault secrets:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd-image-updater/ghcr \
  username="REPLACE_ME" token="REPLACE_ME"

kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd-image-updater/dockerhub \
  username="REPLACE_ME" token="REPLACE_ME"
```

## Step 2: Store Git write-back credentials in Vault

Create a GitHub token with write access to the repository. Store the token in Vault:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd/repo-creds \
  username="REPLACE_ME" token="REPLACE_ME"
```

## Step 3: Let ArgoCD sync

ArgoCD installs ArgoCD Image Updater (chart `1.3.2`) from `infrastructure/argocd-image-updater/`. External Secrets creates two Secrets in the `argocd` namespace:

- `argocd-image-updater-registries`, from `infrastructure/external-secrets/external-secret-argocd-image-updater-registries.yaml`. It reads `kv/argocd-image-updater/ghcr` and `kv/argocd-image-updater/dockerhub` (properties `username` and `token`). It writes the keys `ghcr` and `dockerhub`, each as `<username>:<token>`.
- `repo-homelab`, the ArgoCD repository Secret from `kv/argocd/repo-creds`. Image Updater uses it to push write-back commits.

`infrastructure/argocd-image-updater/values.image-updater` points each registry at its key:

```yaml
config:
  registries:
    - name: GitHub Container Registry
      prefix: ghcr.io
      credentials: secret:argocd/argocd-image-updater-registries#ghcr
    - name: Docker Hub
      prefix: docker.io
      credentials: secret:argocd/argocd-image-updater-registries#dockerhub
```

## Step 4: Examine the image updates

After Image Updater runs, look for new `.argocd-source-app-<name>.yaml` files under `apps/`, for example `apps/jellyfin/.argocd-source-app-jellyfin.yaml`.

## Notes

- The image rules are in `infrastructure/argocd-image-updater/image-updater.yaml` (ImageUpdater `apps`).
- Image Updater commits the updates to `master`. Then ArgoCD auto-syncs them. CI ignores pushes that change only `apps/**/.argocd-source-*.yaml`.
- Each tracked app must have a `kustomization.yaml` file. ArgoCD needs this file to apply the Image Updater overrides.
- Headlamp, Homer, Filebrowser, and Technitium use the `semver` strategy. Headlamp, Homer, and Filebrowser allow only `vX.Y.Z` tags. Technitium allows `X.Y.Z` tags.
- Jellyfin, `alert-summarizer`, and `docs` track the `latest` tag with the `digest` strategy. Thus, each new `latest` image, including each image that CI pushes to GHCR, rolls out through a Git commit. The Jellyfin manifest still says `12.3`, but the `.argocd-source-app-jellyfin.yaml` override pins `latest` by digest.
- The CronJobs in `gmail-classifier`, `drive-organizer`, and `actual-classifier` use `imagePullPolicy: Always` with the `latest` tag. They pull the newest image on each run and have no Image Updater rules.
