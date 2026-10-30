---
title: CI/CD Pipeline with GitHub Actions
description: How GitHub Actions runs pre-commit, kubeconform, secret scans, Python tests, and image builds, and how ArgoCD deploys the changes.
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

This guide tells how GitHub Actions runs CI and how ArgoCD runs CD.

## Step 1: Review the Workflows

`.github/workflows/` has three workflows.

### `ci.yaml` (CI)

`ci.yaml` runs on pull requests and on pushes to `master`. It does not run for changes that touch only `apps/**/.argocd-source-*.yaml`. These files are the Image Updater write-back commits. The workflow has these jobs:

| Job | What it does | When it runs |
| --- | --- | --- |
| `pre-commit` | Runs `pre-commit run --all-files`. The hooks include YAML checks, gitleaks, yamllint, markdownlint, ruff, and kubeconform | Every run |
| `gitleaks` | Scans the full Git history with `gitleaks git --redact` | Every run |
| `docs-build` | Builds the Astro Starlight site with Bun | When `docs/**` or `ci.yaml` changes |
| `docs-push` | Builds the docs image from `docs/` for `linux/amd64` and `linux/arm64` and pushes `ghcr.io/nsudhanva/homelab-docs` with the tags `latest` and the short SHA | Pushes to `master`, when `docs/**` or `ci.yaml` changes |
| `python-changes` | Finds each `apps/*/pyproject.toml` and `packages/*/pyproject.toml`, and selects the projects whose directory, `packages/homelab-ai/`, or `ci.yaml` changed | Every run |
| `test (<project>)` | Runs `uv run ruff check`, `uv run ruff format --check`, `uv run ty check`, and `uv run pytest` for each selected project | When `python-changes` selects a project |
| `push (<app>)` | Builds the image of each selected project that has a `Dockerfile`, with the repo root as the build context, and pushes `ghcr.io/nsudhanva/homelab-<name>` with the tags `latest` and the short SHA | Pushes to `master`, after the tests pass |

kubeconform runs only in the `pre-commit` job. The local hook calls `scripts/run-kubeconform.sh`. The script downloads kubeconform `v0.7.0` and checks its checksum. It validates each YAML file under `apps/`, `infrastructure/`, and `bootstrap/` against Kubernetes `1.37.0`. It skips `app.yaml`, `apps/accounts.yaml`, and the `.argocd-source-*.yaml` files.

The image jobs use the repository root as the build context, so the root `.dockerignore` controls the contents of each image.

### `provision.yaml` (Ansible Provision)

`provision.yaml` runs on pushes to `master` that change `ansible/**` or the workflow file. It also runs on manual runs (`workflow_dispatch`). It joins the tailnet as `tag:ci`, connects to `legion` over SSH, and runs `ansible-playbook -i ansible/inventory/hosts.yaml ansible/site.yaml`. Refer to [GitOps Automation](/how-to/gitops-automation/).

### `tailscale.yaml` (Tailscale)

`tailscale.yaml` runs Terraform in `terraform/tailscale/`. It runs a plan on pull requests and pushes that change `terraform/tailscale/**`. It also runs a plan each Monday to find drift. It applies the plan only on a manual run with **Apply the plan to the tailnet**. Refer to [Manage Tailscale with Terraform](/how-to/tailscale-terraform/).

## Step 2: Configure the GitHub Secrets

`ci.yaml` uses only the built-in `GITHUB_TOKEN` to push images to GHCR. `provision.yaml` needs these repository secrets:

- `TS_OAUTH_CLIENT_ID`
- `TS_OAUTH_SECRET`
- `SSH_PRIVATE_KEY`

`tailscale.yaml` needs `TAILSCALE_TF_OAUTH_CLIENT_ID`, `TAILSCALE_TF_OAUTH_CLIENT_SECRET`, `TF_STATE_R2_ACCESS_KEY_ID`, `TF_STATE_R2_SECRET_ACCESS_KEY`, and `TF_STATE_R2_ENDPOINT`. `scripts/tailscale-terraform.sh github-secrets` sets them from Vault.

## Step 3: Run the Same Checks Locally

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

## Step 4: Let ArgoCD Deploy the Changes

GitHub Actions validates the changes and builds the images. ArgoCD watches this repository and applies the changes through the ApplicationSets. ArgoCD Image Updater writes new `latest` digests of the `docs` and `alert-summarizer` images to Git. The CronJob apps pull `latest` on each run. Refer to [Automated Image Updates](/how-to/image-updates/).
