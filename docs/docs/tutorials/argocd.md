---
sidebar_position: 6
title: ArgoCD and GitOps
---

# ArgoCD and GitOps

## Step: Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
```

:::note

ArgoCD is exposed via Tailscale Ingress in `infrastructure/argocd-ingress/ingress.yaml` (hostname: `argocd`).

:::

## Step: Prepare GitOps bootstrap

Update these files and replace `YOUR_USERNAME` with your GitHub username:

- `bootstrap/root.yaml`
- `bootstrap/templates/infra-appset.yaml`
- `bootstrap/templates/apps-appset.yaml`

Confirm the Longhorn data path in `bootstrap/templates/longhorn.yaml` matches your host.

:::note

If you deploy the docs app, also update the image in `apps/docs/deployment.yaml` and the repository links in `docs/docusaurus.config.ts`.

:::

## Step: Apply the bootstrap

```bash
kubectl apply -f bootstrap/root.yaml
```

## Step: Verify ArgoCD applications

```bash
kubectl get apps -n argocd
```

For adding workloads, see [Deploy Apps With GitOps](../how-to/deploy-apps.md).

## How ApplicationSets work

ApplicationSets watch the `apps/` and `infrastructure/` folders and create applications automatically:

- `apps/*` becomes `app-<folder>`
- `infrastructure/*` becomes `infra-<folder>`

Auto-sync is enabled in the ApplicationSets, so Git is the source of truth.
