---
sidebar_position: 8
title: Expose Headlamp With Tailscale Gateway
---

# Expose Headlamp With Tailscale Gateway

This guide shows how to deploy the Headlamp UI and expose it at `headlamp.sudhanva.me` through the Tailscale Gateway API.

## Step 1: Add the Headlamp app manifests

Create a new app directory under `apps/` with separate manifests for each resource.

Example layout:

- `apps/headlamp/app.yaml`
- `apps/headlamp/namespace.yaml`
- `apps/headlamp/serviceaccount.yaml`
- `apps/headlamp/clusterrolebinding.yaml`
- `apps/headlamp/deployment.yaml`
- `apps/headlamp/service.yaml`
- `apps/headlamp/httproute.yaml`

`app.yaml` defines the app name, path, and namespace.

```yaml
name: headlamp
path: apps/headlamp
namespace: headlamp
```

Expose the service with an `HTTPRoute` that points to the Tailscale Gateway.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: headlamp
  namespace: headlamp
  annotations:
    argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true
spec:
  parentRefs:
  - name: tailscale-gateway
    namespace: tailscale
    sectionName: https
  hostnames:
  - headlamp.sudhanva.me
  rules:
  - backendRefs:
    - name: headlamp
      port: 80
```

## Step 2: Commit and push

ArgoCD watches the repo and applies changes via ApplicationSets.

```bash
git add apps/headlamp
git commit -m "Add headlamp app"
git push
```

## Step 3: Access Headlamp

Open `https://headlamp.sudhanva.me` in your browser. Use a service account token to authenticate.

```bash
kubectl -n headlamp create token headlamp
```

## Step 4: Adjust permissions if needed

The default setup uses `cluster-admin` for the Headlamp service account. If you want read-only access, bind the service account to a more restrictive cluster role.
