---
title: Deploy Headlamp Kubernetes Dashboard
description: How Headlamp runs in this cluster. It signs in with a ServiceAccount token, is exposed through the Tailscale Gateway, and exports metrics to Prometheus.
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

# Expose Headlamp With Tailscale Gateway

Headlamp is a Kubernetes UI. ArgoCD deploys it from `apps/headlamp/` as `app-headlamp`. The Tailscale Gateway exposes it at `headlamp.sudhanva.me`.

## Step 1: Review the app manifests

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

The container listens on port 4466. The Service `headlamp` maps port 80 to 4466. ArgoCD Image Updater tracks semver tags for the image.

## Step 2: Review the HTTPRoute

The HTTPRoute has the ExternalDNS expose annotation and two rules. The first rule sends any path under `/oidc` back to `/` with a `302` redirect. The second rule sends all other requests to the Service:

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

Open `https://headlamp.sudhanva.me` from a tailnet device. Headlamp runs with `-in-cluster -unsafe-use-service-account-token`. It signs in automatically with the token of the `headlamp` ServiceAccount, which has `cluster-admin` privileges. Anyone who can reach the URL on the tailnet has cluster-admin access.

`apps/headlamp/secret-token.yaml` declares the Secret `headlamp-token` of type `kubernetes.io/service-account-token` for the `headlamp` ServiceAccount. Kubernetes fills it with a long-lived token. If the UI asks for a token, read it from that Secret:

```bash
kubectl -n headlamp get secret headlamp-token -o jsonpath='{.data.token}' | base64 -d; echo
```

## Step 4: Cluster role permissions

The file `apps/headlamp/clusterrolebinding.yaml` binds the `headlamp` ServiceAccount to `cluster-admin`. If you want read-only access, change the `roleRef` to the built-in `view` ClusterRole in Git.

## OIDC is not deployed

Headlamp does not use OIDC in this cluster. There is no `kv/headlamp/oidc` Vault path, no `headlamp-oidc` ExternalSecret, and no OIDC flags on the K3s API server. The only OIDC-related item is the `/oidc` redirect rule in the HTTPRoute.

To add OIDC later, add the provider, an ExternalSecret for the client credentials, the Headlamp OIDC arguments, and the `kube-apiserver-arg` OIDC flags in the `k3s_server` Ansible role. Then remove `-unsafe-use-service-account-token`.

## Prometheus Metrics

Headlamp exposes `/metrics` when `HEADLAMP_CONFIG_METRICS_ENABLED` is set. The Deployment sets it to `"true"`. The ServiceMonitor `headlamp` scrapes the `http` port every 30 seconds.

```bash
kubectl -n headlamp get servicemonitors
```

The Headlamp usage graphs need the Metrics Server from `infrastructure/metrics-server/`.
