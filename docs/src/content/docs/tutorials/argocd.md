---
title: Bootstrap ArgoCD for GitOps Deployment
description: Manage Kubernetes infrastructure and applications continuously with ArgoCD ApplicationSets and GitOps automation.
keywords:
  - argocd installation
  - gitops kubernetes
  - argocd applicationset
  - argocd bootstrap
  - kubernetes gitops
  - argocd auto sync
sidebar:
  order: 7
---

# ArgoCD and GitOps

ArgoCD is the main declarative engine for the cluster. It continuously syncs the Kubernetes resources with `HEAD` of this repository (the `master` branch). The install is ArgoCD `v3.5.6`, pinned in `bootstrap/argocd/kustomization.yaml`.

## Step 1: Automated vs Manual Installation

When you run `./scripts/provision.sh`, the Ansible role `ansible/roles/argocd` installs ArgoCD. It also applies the root application automatically.

If you must deploy or recover ArgoCD manually, run these commands:

```bash
kubectl apply --server-side --force-conflicts -k bootstrap/argocd
kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd
```

Get the initial admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
```

:::note

ArgoCD is available through the Gateway API at `argocd.sudhanva.me`.

TLS terminates at Envoy Gateway. Thus, `bootstrap/argocd/kustomization.yaml` applies `bootstrap/argocd/cmd-params-patch.yaml`, which sets `server.insecure: "true"` in the `argocd-cmd-params-cm` ConfigMap.

:::

## Step 2: The ApplicationSet pattern

The root Application `bootstrap` syncs `bootstrap/templates/`, which holds two ApplicationSets:

```mermaid
flowchart TD
  Root["bootstrap/root.yaml"] --> Argo["ArgoCD Engine"]
  Argo --> InfraSet["infrastructure ApplicationSet"]
  Argo --> AppsSet["apps ApplicationSet"]
  InfraSet --> InfraApps["infra-* apps (infrastructure/*)"]
  AppsSet --> UserApps["app-* apps (apps/*)"]
```

- **`bootstrap/templates/infra-appset.yaml`** (ApplicationSet `infrastructure`): Finds each subdirectory in `infrastructure/` and makes one Application named `infra-<directory>` for it.
- **`bootstrap/templates/apps-appset.yaml`** (ApplicationSet `apps`): Finds workloads through `apps/*/app.yaml` and makes one Application named `app-<name>` for each. It deploys them into the namespace from `app.yaml`.

Both ApplicationSets turn on automated sync with prune and self-heal.

## Step 3: Apply the root bootstrap application

To start the reconciliation of all infrastructure components and applications, run this command:

```bash
kubectl apply -f bootstrap/root.yaml
```

ArgoCD reconciles `root.yaml`, which creates the ApplicationSets. The ApplicationSets then generate and sync all applications in the cluster.

## Step 4: Verify application sync status

Make sure that all applications show `Synced` and `Healthy`:

```bash
kubectl get applications -n argocd
```

To add a new workload or infrastructure component, push your manifests directly to Git. ArgoCD deploys them automatically.
