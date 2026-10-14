---
title: Deploy Applications with ArgoCD GitOps
description: Deploy Kubernetes applications with ArgoCD ApplicationSets. Create app manifests, configure Gateway API HTTPRoutes for HTTPS ingress, and let ArgoCD sync from Git.
keywords:
  - argocd deploy application
  - kubernetes gitops deployment
  - argocd applicationset
  - gateway api httproute
  - kubernetes app deployment
  - tailscale gateway ingress
  - externaldns annotation
sidebar:
  order: 3
---

# Deploy Apps With GitOps

This guide shows how to deploy new workloads from this repo through ArgoCD ApplicationSets.

## Step 1: Add a new app directory

Create a folder under `apps/`. Add an `app.yaml` file for the ArgoCD application settings. Add a separate YAML file for each resource.

Example layout:

- `apps/my-app/namespace.yaml`
- `apps/my-app/app.yaml`
- `apps/my-app/deployment.yaml`
- `apps/my-app/service.yaml`
- `apps/my-app/httproute.yaml`

:::note

App namespaces use Pod Security Admission warn and audit labels at the baseline level. These labels do not stop workloads. If a manifest requests privileged features, you get warnings. If your app needs access to the Kubernetes API, set `automountServiceAccountToken: true` and bind a dedicated ServiceAccount.

:::

If you want automatic image updates, add a `kustomization.yaml` file that lists the resources in the folder.

The `app.yaml` file defines the app name, path, and namespace. Example:

```yaml
name: my-app
path: apps/my-app
namespace: my-app
```

ArgoCD creates an application with the name `app-my-app` from this folder. It syncs the application to the namespace in `app.yaml`.

## Step 2: Use Gateway API for HTTPS

Expose the services through the Tailscale Gateway. Use an `HTTPRoute` in the same namespace.

:::note

Hostnames must agree with the wildcard certificate in `infrastructure/gateway/certificate.yaml` (the default is `*.sudhanva.me`).

:::

:::note

ExternalDNS manages only the hostnames that have the annotation `external-dns.alpha.kubernetes.io/expose: "true"`. Some hostnames are split-horizon (public on Cloudflare Pages, private on the tailnet). For these hostnames, do not add the annotation. Manage the public DNS and the Tailscale DNS overrides manually.

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

ArgoCD watches the repo and applies changes through ApplicationSets. After you push your changes, ArgoCD syncs the new app.

:::note

If your app must share data with a different app, put the two apps in the same namespace. To do this, set the same namespace in the two `app.yaml` files. Alternatively, use an RWX volume that you intentionally share. Do not refer to a PVC in a different namespace.

:::

## Step 4: Verify in ArgoCD

```bash
kubectl get apps -n argocd
```

## Step 5: Trigger a manual sync

Use this step if the app is out of sync or if auto-sync is disabled.

:::note

If auto-sync is enabled on the ApplicationSet, ArgoCD reconciles automatically after your push.

:::

### Option A: Sync in the UI

Open the ArgoCD UI. Select the application. Click Sync.

### Option B: Sync with CLI

```bash
argocd app sync <app-name>
argocd app wait <app-name> --health
```
