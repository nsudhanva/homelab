---
title: CI And CD With GitHub Actions
---

# CI And CD With GitHub Actions

This guide explains how CI runs in GitHub Actions and how CD flows through ArgoCD and the docs image build.

## Step 1: Review the workflows

These workflows live in `.github/workflows/`:

- `ci.yaml` runs pre-commit, kubeconform validation, a docs build check, and pushes the docs image on changes under `docs/`.
- `cluster-smoke.yaml` is a manual and scheduled workflow that connects to the tailnet and runs `kubectl get nodes` and `kubectl get pods -A`.

## Step 2: Configure GitHub secrets

Add these repository secrets for the tailnet-enabled workflow:

- `TS_OAUTH_CLIENT_ID`
- `TS_OAUTH_SECRET`
- `KUBECONFIG_B64`

`KUBECONFIG_B64` should be a base64-encoded kubeconfig that can reach the cluster API on the tailnet.

## Step 3: Understand what each check covers

CI validation focuses on the Kubernetes and GitOps manifests in this repo.

| Area | Coverage | Workflow |
| --- | --- | --- |
| `apps/` | YAML lint, schema validation (excluding `app.yaml`) | `ci.yaml` |
| `infrastructure/` | YAML lint, schema validation | `ci.yaml` |
| `bootstrap/` | YAML lint, schema validation | `ci.yaml` |
| `docs/` | Docusaurus build and image push | `ci.yaml` |

## Step 4: Trigger a cluster smoke test

Run the workflow manually when you want to validate the live cluster health over Tailscale.

- Workflow: `Cluster Smoke` in GitHub Actions
- Checks: `kubectl get nodes`, `kubectl get pods -A`, and ArgoCD app status

The workflow also runs every six hours via a scheduled trigger.

## Step 5: Rely on ArgoCD for CD

ArgoCD watches this repo and applies changes via ApplicationSets. GitHub Actions validates and builds artifacts, while ArgoCD handles the deployment and reconciliation in-cluster.
