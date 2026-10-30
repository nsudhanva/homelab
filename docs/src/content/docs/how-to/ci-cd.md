---
title: CI/CD Pipeline with GitHub Actions
description: How GitHub Actions runs pre-commit, kubeconform, secret scans, Python tests, and image builds, and how ArgoCD handles deployment.
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

This guide shows how CI runs in GitHub Actions. It also shows how CD goes through ArgoCD.

## Step 1: Review the workflows

There are two workflows in `.github/workflows/`.

### `ci.yaml` (CI)

`ci.yaml` runs on pull requests and on pushes to `master`. It ignores changes that touch only `apps/**/.argocd-source-*.yaml`, which are the Image Updater write-back commits. It has these jobs:

| Job | What it does | When it runs |
| --- | --- | --- |
| `pre-commit` | Runs `pre-commit run --all-files`. The hooks include YAML checks, gitleaks, yamllint, markdownlint, ruff, and kubeconform | Every run |
| `gitleaks` | Scans the full Git history with `gitleaks git --redact` | Every run |
| `docs-build` | Builds the Astro Starlight site with Bun | When `docs/**` or `ci.yaml` changes |
| `docs-push` | Builds the docs image from `docs/` for `linux/amd64` and `linux/arm64` and pushes `ghcr.io/nsudhanva/homelab-docs` with the tags `latest` and the short SHA | Pushes to `master`, when `docs/**` or `ci.yaml` changes |
| `python-changes` | Finds each `apps/*/pyproject.toml` and `packages/*/pyproject.toml`, and selects the projects whose directory, `packages/homelab-ai/`, or `ci.yaml` changed | Every run |
| `test (<project>)` | Runs `uv run ruff check`, `uv run ruff format --check`, `uv run ty check`, and `uv run pytest` for each selected project | When `python-changes` selects a project |
| `push (<app>)` | Builds the image of each selected project that has a `Dockerfile`, with the repo root as the build context, and pushes `ghcr.io/nsudhanva/homelab-<name>` with the tags `latest` and the short SHA | Pushes to `master`, after the tests pass |

kubeconform runs only inside the `pre-commit` job. The local hook calls `scripts/run-kubeconform.sh`. The script downloads kubeconform `v0.7.0`, checks its checksum, and validates every YAML file under `apps/`, `infrastructure/`, and `bootstrap/` against Kubernetes `1.37.0`. It skips `app.yaml`, `apps/accounts.yaml`, and the `.argocd-source-*.yaml` files.

The image jobs build with the repo root as the context, so the root `.dockerignore` controls what goes into every image.

### `provision.yaml` (Ansible Provision)

`provision.yaml` runs on pushes to `master` that change `ansible/**` or the workflow file, and on manual runs (`workflow_dispatch`). It joins the tailnet as `tag:ci`, connects to `legion` over SSH, and runs `ansible-playbook -i ansible/inventory/hosts.yaml ansible/site.yaml`. Refer to [GitOps Automation](/how-to/gitops-automation/).

### `tailscale.yaml` (Tailscale)

`tailscale.yaml` runs Terraform in `terraform/tailscale/`. It plans on pull requests and pushes that change `terraform/tailscale/**`, and every Monday to detect drift. It applies only when you run it by hand with **Apply the plan to the tailnet**. Refer to [Manage Tailscale with Terraform](/how-to/tailscale-terraform/).

## Step 2: Configure GitHub secrets

`ci.yaml` uses only the built-in `GITHUB_TOKEN` to push images to GHCR. `provision.yaml` needs these repository secrets:

- `TS_OAUTH_CLIENT_ID`
- `TS_OAUTH_SECRET`
- `SSH_PRIVATE_KEY`

`tailscale.yaml` needs `TAILSCALE_TF_OAUTH_CLIENT_ID`, `TAILSCALE_TF_OAUTH_CLIENT_SECRET`, `TF_STATE_R2_ACCESS_KEY_ID`, `TF_STATE_R2_SECRET_ACCESS_KEY`, and `TF_STATE_R2_ENDPOINT`. `scripts/tailscale-terraform.sh github-secrets` sets them from Vault.

## Step 3: Run the same checks locally

Before you push, run the hooks that CI runs:

```bash
pre-commit run --all-files
```

For a Python project, run the checks in the project directory:

```bash
uv run ruff check
uv run ruff format --check
uv run ty check
uv run pytest
```

## Step 4: Rely on ArgoCD for CD

ArgoCD watches this repo and applies changes through ApplicationSets. GitHub Actions validates and builds artifacts. ArgoCD does the deployment and reconciliation in the cluster. Image Updater rolls out new `latest` digests for the `docs` and `alert-summarizer` images through Git commits. The CronJob apps pull `latest` on each run. Refer to [Automated Image Updates](/how-to/image-updates/).
