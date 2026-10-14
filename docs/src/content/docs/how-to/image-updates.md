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

ArgoCD installs ArgoCD Image Updater. It also creates the registry secret and the repository credentials.

## Step 4: Examine the image updates

After Image Updater runs, look for new `.argocd-source-<appName>.yaml` files under `apps/`.

## Notes

- The image rules are in `infrastructure/argocd-image-updater/image-updater.yaml`.
- External Secrets creates the registry secrets in `infrastructure/external-secrets/`.
- Image Updater commits the updates to the tracked branch (`master`). Then ArgoCD can auto-sync them.
- Each app must have a `kustomization.yaml` file. ArgoCD needs this file to apply the Image Updater overrides.
- Third-party images (Headlamp, Homer, Filebrowser) use semver tags. Jellyfin and the in-house Deployments (`alert-summarizer`, `docs`) track the `latest` tag by digest. Thus, each image that CI pushes to GHCR rolls out through a Git commit.
- Some CronJobs use `imagePullPolicy: Always` with the `latest` tag (`gmail-classifier`, `drive-organizer`, `actual-classifier`). These CronJobs pull the newest image on each run. They do not need Image Updater rules.
