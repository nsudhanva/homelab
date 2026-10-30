---
title: Deploy Headlamp Kubernetes Dashboard
description: How Headlamp runs in this cluster. It signs in with a ServiceAccount token, the Tailscale Gateway exposes it, and Prometheus scrapes its metrics.
keywords:
  - headlamp kubernetes
  - kubernetes dashboard
  - headlamp service account token
  - kubernetes ui
  - headlamp metrics
  - tailscale gateway headlamp
sidebar:
  order: 17
---

Headlamp is a Kubernetes UI. ArgoCD deploys it from `apps/headlamp/` as `app-headlamp`. The Tailscale Gateway exposes it at `headlamp.sudhanva.me`.

## Step 1: Review the App Manifests

The app has one manifest for each resource:

- `apps/headlamp/app.yaml`
- `apps/headlamp/kustomization.yaml`
- `apps/headlamp/namespace.yaml`
- `apps/headlamp/serviceaccount.yaml`
- `apps/headlamp/clusterrolebinding.yaml`
- `apps/headlamp/secret-token.yaml`
- `apps/headlamp/deployment.yaml`
- `apps/headlamp/service.yaml`
- `apps/headlamp/servicemonitor.yaml`
- `apps/headlamp/httproute.yaml`

The `app.yaml` file defines the app name, the path, and the namespace:

```yaml
name: headlamp
path: apps/headlamp
namespace: headlamp
```

The Deployment runs `ghcr.io/headlamp-k8s/headlamp` with these arguments:

```yaml
args:
- -in-cluster
- -unsafe-use-service-account-token
- -plugins-dir=/headlamp/plugins
```

The container listens on port 4466. The Service `headlamp` maps port 80 to port 4466. ArgoCD Image Updater tracks the semver tags of the image.

## Step 2: Review the HTTPRoute

The HTTPRoute has the ExternalDNS expose annotation and two rules. The first rule redirects each path under `/oidc` to `/` with a `302` status. The second rule sends all other requests to the Service:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: headlamp
  namespace: headlamp
  annotations:
    argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true
    external-dns.alpha.kubernetes.io/expose: "true"
    external-dns.alpha.kubernetes.io/cloudflare-proxied: "false"
spec:
  parentRefs:
  - name: tailscale-gateway
    namespace: tailscale
    sectionName: https
  hostnames:
  - headlamp.sudhanva.me
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /oidc
    filters:
    - type: RequestRedirect
      requestRedirect:
        path:
          type: ReplaceFullPath
          replaceFullPath: /
        statusCode: 302
  - backendRefs:
    - name: headlamp
      port: 80
```

## Step 3: Access Headlamp

Open `https://headlamp.sudhanva.me` from a tailnet device. Headlamp runs with `-in-cluster -unsafe-use-service-account-token`. It signs in automatically with the token of the `headlamp` ServiceAccount. This ServiceAccount has `cluster-admin` privileges, so each user who can reach the URL on the tailnet has cluster-admin access.

`apps/headlamp/secret-token.yaml` declares the Secret `headlamp-token` of type `kubernetes.io/service-account-token` for the `headlamp` ServiceAccount. Kubernetes writes a long-lived token to this Secret. If the UI asks for a token, read it from the Secret:

```bash
kubectl -n headlamp get secret headlamp-token -o jsonpath='{.data.token}' | base64 -d; echo
```

## Step 4: Review the Cluster Role Permissions

The file `apps/headlamp/clusterrolebinding.yaml` binds the `headlamp` ServiceAccount to `cluster-admin`. For read-only access, change the `roleRef` to the built-in `view` ClusterRole in Git.

## Authentication Scope

Headlamp signs in only with the ServiceAccount token. The cluster has no OIDC provider for Headlamp or for the K3s API server.

## Prometheus Metrics

Headlamp exposes `/metrics` when `HEADLAMP_CONFIG_METRICS_ENABLED` is set. The Deployment sets it to `"true"`. The ServiceMonitor `headlamp` scrapes the `http` port every 30 seconds.

```bash
kubectl -n headlamp get servicemonitors
```

The Headlamp usage graphs need the Metrics Server from `infrastructure/metrics-server/`.
