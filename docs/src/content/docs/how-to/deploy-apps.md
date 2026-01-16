---
title: Deploy Apps With GitOps
---

# Deploy Apps With GitOps

This guide shows how to use this repo to deploy new workloads through ArgoCD ApplicationSets.

## Step 1: Add a new app directory

Create a folder under `apps/` and include an `app.yaml` file to define the ArgoCD application settings, plus separate YAML files for each resource.

Example layout:

- `apps/my-app/namespace.yaml`
- `apps/my-app/app.yaml`
- `apps/my-app/deployment.yaml`
- `apps/my-app/service.yaml`
- `apps/my-app/httproute.yaml`

:::note

App namespaces use Pod Security Admission warn and audit labels at the baseline level. They do not block workloads, but you will see warnings if a manifest requests privileged features. If your app needs Kubernetes API access, set `automountServiceAccountToken: true` and bind a dedicated ServiceAccount.

:::

If you want automated image updates, also include a `kustomization.yaml` that lists the resources in the folder.

`app.yaml` defines the app name, path, and namespace. Example:

```yaml
name: my-app
path: apps/my-app
namespace: my-app
```

ArgoCD will create an application named `app-my-app` from this folder and sync it to the namespace defined in `app.yaml`.

## Step 2: Use Gateway API for HTTPS

Expose services through the Tailscale Gateway using an `HTTPRoute` in the same namespace.

:::note

Hostnames must fit the wildcard certificate in `infrastructure/gateway/certificate.yaml` (by default `*.sudhanva.me`).

:::

:::note

ExternalDNS only manages hostnames annotated with `external-dns.alpha.kubernetes.io/expose: "true"`. For split-horizon hostnames (public on Cloudflare Pages, private on tailnet), omit the annotation and manage public DNS and Tailscale DNS overrides manually.

:::

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: my-app
  namespace: my-app
  annotations:
    external-dns.alpha.kubernetes.io/expose: "true"
    external-dns.alpha.kubernetes.io/cloudflare-proxied: "false"
spec:
  parentRefs:
  - name: tailscale-gateway
    namespace: tailscale
    sectionName: https
  hostnames:
  - my-app.sudhanva.me
  rules:
  - backendRefs:
    - name: my-app
      port: 80
```

## Step 3: Commit and push

ArgoCD watches the repo and applies changes via ApplicationSets. Once your changes are pushed, ArgoCD will sync the new app.

:::note

If your app needs to share data with another app, place them in the same namespace (by pointing both `app.yaml` files at the same namespace) or use an RWX volume that is intentionally shared. Avoid cross-namespace PVC references.

:::

## Step 4: Verify in ArgoCD

```bash
kubectl get apps -n argocd
```

## Step 5: Trigger a manual sync

Use this if the app is out of sync or if auto-sync is disabled.

:::note

If auto-sync is enabled on the ApplicationSet, ArgoCD will reconcile automatically after your push.

:::

### Option A: Sync in the UI

Open the ArgoCD UI, select the application, then click Sync.

### Option B: Sync with CLI

```bash
argocd app sync <app-name>
argocd app wait <app-name> --health
```
