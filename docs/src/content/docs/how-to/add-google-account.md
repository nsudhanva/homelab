---
title: How to Manage Multi-Account Google Workloads with Declarative IaC
description: Configure, securely store, and deploy multiple isolated Google accounts for Gmail Classifier and Drive Organizer using a declarative account matrix, HashiCorp Vault, and GitOps.
keywords:
  - multi-account google
  - declarative account matrix
  - gmail classifier accounts
  - drive organizer multi-account
  - vault google oauth
  - kubernetes gitops
sidebar:
  order: 21
---

# How to Manage Multi-Account Google Workloads with Declarative IaC

This problem-oriented guide explains how to declaratively configure, store credentials for, and deploy multiple Google accounts across the homelab AI pipeline (`apps/gmail-classifier` and `apps/drive-organizer`).

All Google accounts are treated uniformly as identical peer entities. There are no hierarchy tiers. Every account is assigned a descriptive nickname (for example, `personal`, `work`, or `family`). Account configuration is managed purely through Infrastructure as Code (IaC) without manual or ad-hoc workload commands.

## Architecture and Design Principles

The multi-account architecture is built around three core principles:

- **Declarative Single Source of Truth**: The complete cluster account matrix is defined in `apps/accounts.yaml`. Symmetrical Kubernetes manifests (`CronJob` and `ExternalSecret`) are generated deterministically via `scripts/generate-account-manifests.py`.
- **Fault-Domain & Secret Isolation**: Every account executes in an isolated non-root Pod and distinct CronJob instance. Each account mounts only its own Kubernetes secret synchronized from a dedicated Vault path (`kv/google/accounts/<nickname>`), preventing cross-account token access or cascaded failures.
- **Resource Staggering**: Cron schedules are staggered across fifteen-minute intervals (for example, `01:00 UTC` for `personal` Gmail, `01:15 UTC` for `work` Gmail) to eliminate GPU slot contention on the local Gemma 4 model server (`llama-server`).
- **Notification Routing**: Notifications include account-specific header badges (`[Personal]`, `[Work]`) and optionally target distinct Telegram forum topics via `TELEGRAM_TOPIC_ID`.

## Step 1: Obtain Google OAuth Credentials

Create an OAuth 2.0 Client in the Google Cloud Console for the target Google account:

- Navigate to the Google Cloud Console APIs & Services Credentials page.
- Create an OAuth Client ID with application type **Desktop app**.
- Ensure the required scopes are enabled:
  - Gmail Classifier: `https://www.googleapis.com/auth/gmail.modify`
  - Drive Organizer: `https://www.googleapis.com/auth/drive`
- Run `scripts/get-google-oauth-token.py --account <nickname>` to generate the initial `refresh_token`.

## Step 2: Store Credentials in HashiCorp Vault

Store the credentials in HashiCorp Vault under the standard account path. Never commit credentials to git:

```bash
# Store credentials for any account by its nickname
vault kv put kv/google/accounts/personal \
  client_id="YOUR_PERSONAL_CLIENT_ID" \
  client_secret="YOUR_PERSONAL_CLIENT_SECRET" \
  refresh_token="YOUR_PERSONAL_REFRESH_TOKEN"

vault kv put kv/google/accounts/work \
  client_id="YOUR_WORK_CLIENT_ID" \
  client_secret="YOUR_WORK_CLIENT_SECRET" \
  refresh_token="YOUR_WORK_REFRESH_TOKEN"

# Store shared Telegram notification bot token
vault kv put kv/telegram/bot \
  token="YOUR_TELEGRAM_BOT_TOKEN"
```

## Step 3: Declare Accounts in the Account Matrix

Add the account entry to `apps/accounts.yaml` using its nickname:

```yaml
accounts:
  - nickname: personal
    schedule:
      gmail: "0 1 * * *"
      drive: "0 2 * * *"
    vault_path: google/accounts/personal
  - nickname: work
    schedule:
      gmail: "15 1 * * *"
      drive: "15 2 * * *"
    vault_path: google/accounts/work
```

## Step 4: Reconcile Manifests via Code

Run the manifest generator script to produce the symmetrical Kubernetes manifests:

```bash
uv run --with pyyaml scripts/generate-account-manifests.py
```

To verify that all manifests in git are in sync with `apps/accounts.yaml` without writing changes:

```bash
uv run --with pyyaml scripts/generate-account-manifests.py --check
```

The generator produces:

- Symmetrical CronJobs: `cronjob-primary.yaml`, `cronjob-secondary.yaml`
- Symmetrical ExternalSecrets: `secret-primary.yaml`, `secret-secondary.yaml`
- Updated `kustomization.yaml` resource lists

## Step 5: Verify GitOps Synchronization

Commit the updated matrix and generated manifests to git. ArgoCD automatically synchronizes the resources into the cluster:

```bash
# Check ExternalSecret sync status
kubectl -n gmail-classifier get externalsecrets
kubectl -n drive-organizer get externalsecrets

# Check active CronJob schedules
kubectl -n gmail-classifier get cronjobs
kubectl -n drive-organizer get cronjobs
```

Both apps report active schedules with zero manual intervention required.

## Step 6: Autonomous Label Discovery for New Accounts

When adding a fresh Google account with a sparse or empty custom label taxonomy, the classifier does not dump legitimate incoming messages into `ai-review`. With `ALLOW_LABEL_CREATION=true` (enabled by default across all accounts generated by `scripts/generate-account-manifests.py`), the local LLM autonomously discovers and creates high-level canonical labels (such as `Newsletters`, `Travel`, `Entertainment`, `Shopping`, `Finance`, `Social`) directly in Gmail on first match. Subsequent runs reuse the newly created labels seamlessly.
