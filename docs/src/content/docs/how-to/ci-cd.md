---
title: CI/CD Pipeline with GitHub Actions
description: Configure GitHub Actions for Kubernetes manifest validation, pre-commit checks, and docs image builds. Learn how CI validation and ArgoCD deployment work together.
keywords:
  - github actions kubernetes
  - kubeconform validation
  - pre-commit kubernetes
  - kubernetes ci cd
  - argocd cd
  - github actions tailscale
  - kubernetes manifest validation
sidebar:
  order: 15
---

# CI And CD With GitHub Actions

This guide shows how CI runs in GitHub Actions. It also shows how CD goes through ArgoCD and the docs image build.

## Step 1: Review the workflows

These workflows are in `.github/workflows/`:

- `ci.yaml` runs pre-commit, kubeconform validation, and a docs build check. When files under `docs/` change, it also pushes the docs image.
- `ci.yaml` also tests the Python projects listed in `.github/python-projects.json`. A project runs ruff, ty, and pytest when its directory or `packages/homelab-ai` changes. On `master`, CI then pushes the image of each changed project to `ghcr.io/nsudhanva/homelab-<name>`.
- `cluster-smoke.yaml` is a manual and scheduled workflow. It connects to the tailnet and runs `kubectl get nodes` and `kubectl get pods -A`.

## Step 2: Configure GitHub secrets

Add these repository secrets for the workflow that uses the tailnet:

- `TS_OAUTH_CLIENT_ID`
- `TS_OAUTH_SECRET`
- `KUBECONFIG_B64`

`KUBECONFIG_B64` must be a base64-encoded kubeconfig that can connect to the cluster API on the tailnet.

## Step 3: Understand what each check covers

CI validation examines the Kubernetes and GitOps manifests in this repo.

| Area | Coverage | Workflow |
| --- | --- | --- |
| `apps/` | YAML lint, schema validation (excluding `app.yaml`) | `ci.yaml` |
| `infrastructure/` | YAML lint, schema validation | `ci.yaml` |
| `bootstrap/` | YAML lint, schema validation | `ci.yaml` |
| `docs/` | Astro Starlight build and container image push | `ci.yaml` |
| Python projects | ruff, ty, pytest, and container image push | `ci.yaml` |

## Step 4: Trigger a cluster smoke test

To examine the health of the live cluster over Tailscale, run the workflow manually.

- Workflow: `Cluster Smoke` in GitHub Actions
- Checks: `kubectl get nodes`, `kubectl get pods -A`, and ArgoCD app status

A scheduled trigger also runs the workflow every six hours.

## Step 5: Rely on ArgoCD for CD

ArgoCD watches this repo and applies changes through ApplicationSets. GitHub Actions validates and builds artifacts. ArgoCD does the deployment and reconciliation in the cluster.
