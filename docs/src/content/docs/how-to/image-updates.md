---
title: Automated Container Image Updates with ArgoCD
description: Configure ArgoCD Image Updater to track container image versions and commit the updates to Git.
keywords:
  - argocd image updater
  - automated image updates
  - container image versioning
  - gitops image automation
  - ghcr credentials
  - kustomization image override
sidebar:
  order: 6
---

# Automated Image Updates

This guide configures ArgoCD Image Updater. Image Updater tracks container images and commits the updates to Git.

## Step 1: Store registry credentials in Vault

Create this Vault secret for GHCR. Image Updater reads Docker Hub anonymously, so Docker Hub needs no secret.

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd-image-updater/ghcr \
  username="REPLACE_ME" token="REPLACE_ME"
```

## Step 2: Store Git write-back credentials in Vault

Create a GitHub token with write access to the repository. Store the token in Vault.

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd/repo-creds \
  username="REPLACE_ME" token="REPLACE_ME"
```

## Step 3: Let ArgoCD sync

ArgoCD installs ArgoCD Image Updater (chart `1.3.2`) from `infrastructure/argocd-image-updater/`. External Secrets creates two Secrets in the `argocd` namespace:

- `argocd-image-updater-registries`, from `infrastructure/external-secrets/external-secret-argocd-image-updater-registries.yaml`. It reads `kv/argocd-image-updater/ghcr` (properties `username` and `token`) and writes the key `ghcr` as `<username>:<token>`.
- `repo-homelab`, the ArgoCD repository Secret from `kv/argocd/repo-creds`. Image Updater uses it to push write-back commits.

The file `infrastructure/argocd-image-updater/values.image-updater` points the GHCR registry at the `ghcr` key. The Docker Hub registry has no `credentials` entry, so Image Updater reads Docker Hub anonymously.

```yaml
config:
  registries:
    - name: GitHub Container Registry
      prefix: ghcr.io
      credentials: secret:argocd/argocd-image-updater-registries#ghcr
    - name: Docker Hub
      prefix: docker.io
```

## Step 4: Examine the image updates

When Image Updater finds a new image, it writes a `.argocd-source-app-<name>.yaml` file under `apps/`. An example is `apps/jellyfin/.argocd-source-app-jellyfin.yaml`.

## Notes

- The image rules are in `infrastructure/argocd-image-updater/image-updater.yaml` (ImageUpdater `apps`).
- Image Updater commits the updates to `master`, and ArgoCD auto-syncs them. CI ignores pushes that change only `apps/**/.argocd-source-*.yaml`.
- Each tracked app must have a `kustomization.yaml` file. ArgoCD needs this file to apply the Image Updater overrides.
- Headlamp, Homer, Filebrowser, and Technitium use the `semver` strategy. Headlamp, Homer, and Filebrowser allow only `vX.Y.Z` tags. Technitium allows `X.Y.Z` tags.
- Jellyfin, `alert-summarizer`, and `docs` track the `latest` tag with the `digest` strategy. Each new `latest` image, including each image that CI pushes to GHCR, rolls out through a Git commit.
- The Jellyfin Deployment sets the tag `12.3`. The `.argocd-source-app-jellyfin.yaml` override replaces it with `latest`, pinned by digest.
- The CronJobs in `gmail-classifier`, `drive-organizer`, and `actual-classifier` use `imagePullPolicy: Always` with the `latest` tag. They pull the newest image on each run and have no Image Updater rules.
