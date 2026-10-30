---
title: Deploy Applications with ArgoCD GitOps
description: Deploy an application with the ArgoCD ApplicationSets. Create the app manifests, add a Gateway API HTTPRoute for HTTPS, and let ArgoCD sync from Git.
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

This guide tells how to deploy a workload from this repository through the ArgoCD ApplicationSets.

## Step 1: Add an App Directory

Create a directory under `apps/`. Add an `app.yaml` file for the ArgoCD application settings. Add a separate YAML file for each resource.

Example layout:

- `apps/my-app/namespace.yaml`
- `apps/my-app/app.yaml`
- `apps/my-app/deployment.yaml`
- `apps/my-app/service.yaml`
- `apps/my-app/httproute.yaml`

:::note

Most app namespaces (`actual-budget`, `docs`, `headlamp`, `home-assistant`, `homer`, `llama`, `media`, `technitium`) set the Pod Security Admission labels `warn` and `audit` at the `baseline` level. These labels do not block workloads. If a manifest requests privileged features, the API server returns warnings. These namespaces are different:

- `drive-organizer` also sets `enforce: baseline`, so the API server rejects pods that break the baseline policy.
- `gmail-classifier` and `actual-classifier` have no Pod Security labels.

Add the `warn` and `audit` labels to the `namespace.yaml` of a new app. If your app needs access to the Kubernetes API, set `automountServiceAccountToken: true` and bind a dedicated ServiceAccount.

:::

For automatic image updates, add a `kustomization.yaml` file that lists the resources in the directory.

The `app.yaml` file defines the app name, the path, and the namespace. Example:

```yaml
name: my-app
path: apps/my-app
namespace: my-app
```

ArgoCD creates the Application `app-my-app` from this directory. It syncs the Application to the namespace in `app.yaml`.

## Step 2: Use the Gateway API for HTTPS

Expose the Service through the Tailscale Gateway. Put an `HTTPRoute` in the namespace of the app.

:::note

The hostnames must agree with the wildcard certificate in `infrastructure/gateway/certificate.yaml` (`*.sudhanva.me`).

:::

:::note

ExternalDNS manages only the hostnames that have the annotation `external-dns.alpha.kubernetes.io/expose: "true"`. The docs hostnames (`homelab.sudhanva.me` and `docs.sudhanva.me`) use split-horizon DNS. Each has a public record that ExternalDNS does not manage, and a private answer on the tailnet. Do not add the annotation to these hostnames. Manage their public DNS records manually.

If you add an HTTPRoute, also add it to the Homer dashboard in `apps/homer/configmap.yaml`. The `tailscale-dns-updater` CronJob adds the hostname to the tailnet resolver within 10 minutes.

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

## Step 3: Commit and Push

ArgoCD watches the repository and applies changes through the ApplicationSets. After you push, ArgoCD syncs the new app.

:::note

If two apps must share data, put them in the same namespace. Set the same namespace in the two `app.yaml` files. As an alternative, use a ReadWriteMany (RWX) volume that the two apps share. Do not refer to a PVC in a different namespace.

:::

## Step 4: Verify in ArgoCD

```bash
kubectl get apps -n argocd
```

## Step 5: Start a Manual Sync

The ApplicationSets enable automated sync, so ArgoCD reconciles after your push. Use this step if the app stays out of sync.

### Option A: Sync in the UI

Open the ArgoCD UI. Select the application. Click **Sync**.

### Option B: Sync with the CLI

```bash
argocd app sync <app-name>
argocd app wait <app-name> --health
```
