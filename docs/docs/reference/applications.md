---
sidebar_position: 5
title: Applications Catalog
---

# Applications Catalog

This page lists the applications already defined in `apps/`.

## Media namespace

The `media` namespace is shared by Jellyfin and Filebrowser so they can use the same PVCs.

- Namespace definition: `apps/media/namespace.yaml`
- ArgoCD app: `apps/media/app.yaml`

## Jellyfin

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/media/namespace.yaml` | Shared `media` namespace |
| App config | `apps/jellyfin/app.yaml` | ArgoCD app definition |
| Deployment | `apps/jellyfin/deployment.yaml` | Uses Intel iGPU by default |
| Service | `apps/jellyfin/service.yaml` | ClusterIP on port 80 |
| HTTPRoute | `apps/jellyfin/httproute.yaml` | `jellyfin.sudhanva.me` |
| PVCs | `apps/jellyfin/pvc-config.yaml` and `apps/jellyfin/pvc-media.yaml` | Longhorn storage |

## Filebrowser

| Item | Path | Notes |
| --- | --- | --- |
| App config | `apps/filebrowser/app.yaml` | ArgoCD app definition |
| Deployment | `apps/filebrowser/deployment.yaml` | No auth, mounts Jellyfin media |
| Service | `apps/filebrowser/service.yaml` | ClusterIP on port 80 |
| HTTPRoute | `apps/filebrowser/httproute.yaml` | `filebrowser.sudhanva.me` |

## Docs site

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/docs/namespace.yaml` | Dedicated `docs` namespace |
| App config | `apps/docs/app.yaml` | ArgoCD app definition |
| Deployment | `apps/docs/deployment.yaml` | Uses `ghcr.io/nsudhanva/homelab-docs:latest` |
| Service | `apps/docs/service.yaml` | ClusterIP on port 80 |
| HTTPRoute | `apps/docs/httproute.yaml` | `docs.sudhanva.me` split-horizon (public Pages + tailnet Gateway) |

## Headlamp

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/headlamp/namespace.yaml` | Dedicated `headlamp` namespace |
| App config | `apps/headlamp/app.yaml` | ArgoCD app definition |
| Deployment | `apps/headlamp/deployment.yaml` | `ghcr.io/headlamp-k8s/headlamp:v0.39.0` |
| Service | `apps/headlamp/service.yaml` | ClusterIP on port 80 |
| HTTPRoute | `apps/headlamp/httproute.yaml` | `headlamp.sudhanva.me` |
| ServiceMonitor | `apps/headlamp/servicemonitor.yaml` | Prometheus scrape config |

## Home dashboard (Homer)

| Item | Path | Notes |
| --- | --- | --- |
| Namespace | `apps/homer/namespace.yaml` | Dedicated `homer` namespace |
| App config | `apps/homer/app.yaml` | ArgoCD app definition |
| ConfigMap | `apps/homer/configmap.yaml` | Homer `config.yml` |
| Deployment | `apps/homer/deployment.yaml` | Uses `b4bz/homer:v25.11.1` |
| Service | `apps/homer/service.yaml` | ClusterIP on port 80 |
| HTTPRoute | `apps/homer/httproute.yaml` | `home.sudhanva.me` |
