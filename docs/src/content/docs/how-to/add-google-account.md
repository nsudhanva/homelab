---
title: How to Manage Multi-Account Google Workloads with Declarative IaC
description: Configure, store, and deploy isolated Google accounts for Gmail Classifier and Drive Organizer with a declarative account matrix, HashiCorp Vault, and GitOps.
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

This guide shows how to add more than one Google account to the homelab AI pipeline (`apps/gmail-classifier` and `apps/drive-organizer`). You configure each account declaratively, keep its credentials in Vault, and deploy it through GitOps.

All Google accounts are equal peers. There are no hierarchy tiers. Each account has a nickname that describes it (for example, `personal`, `work`, or `family`). You manage the account configuration only through Infrastructure as Code (IaC). Do not use manual or ad-hoc workload commands.

## Architecture and Design Principles

The multi-account design follows these principles:

- **Declarative Single Source of Truth**: The file `apps/accounts.yaml` holds the full account matrix for the cluster. The script `scripts/generate-account-manifests.py` makes the symmetrical Kubernetes manifests (`CronJob` and `ExternalSecret`) from this file. The output is the same each time.
- **Fault-Domain & Secret Isolation**: Each account runs in its own non-root Pod and its own CronJob. Each account mounts only its own Kubernetes secret, which syncs from its own Vault path (`kv/google/accounts/<nickname>`). Thus, one account cannot read the tokens of a different account, and one failure cannot cause more failures.
- **Resource Staggering**: The cron schedules start 15 minutes apart (for example, `01:00 UTC` for `personal` Gmail, `01:15 UTC` for `work` Gmail). Thus, the accounts do not compete for the GPU slot on the local Gemma 4 model server (`llama-server`).
- **Notification Routing**: Each notification has a header badge for its account (`[Personal]`, `[Work]`). As an option, it can go to a different Telegram forum topic through `TELEGRAM_TOPIC_ID`.

## Step 1: Get Google OAuth Credentials

In the Google Cloud Console, create an OAuth 2.0 Client for the target Google account:

- Go to the Google Cloud Console APIs & Services Credentials page.
- Create an OAuth Client ID with the application type **Desktop app**.
- Make sure that these necessary scopes are enabled:
  - Gmail Classifier: `https://www.googleapis.com/auth/gmail.modify`
  - Drive Organizer: `https://www.googleapis.com/auth/drive`
- Run `scripts/get-google-oauth-token.py --account <nickname>` to make the initial `refresh_token`.

## Step 2: Store Credentials in HashiCorp Vault

Never commit credentials to git. Put the credentials in HashiCorp Vault under the standard account path:

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

Add the account entry to `apps/accounts.yaml` with its nickname:

```yaml
accounts:
  - nickname: personal
    schedule:
      gmail: "0 1 * * *"
      gmail_mark_read: "0 4 * * 0"
      drive: "0 2 * * *"
    vault_path: google/accounts/personal
  - nickname: work
    schedule:
      gmail: "15 1 * * *"
      gmail_mark_read: "15 4 * * 0"
      drive: "15 2 * * *"
    vault_path: google/accounts/work
```

## Step 4: Reconcile Manifests Through Code

Run the manifest generator script to make the symmetrical Kubernetes manifests:

```bash
uv run --with pyyaml scripts/generate-account-manifests.py
```

To make sure that all manifests in git agree with `apps/accounts.yaml`, run the check mode. This mode does not write changes:

```bash
uv run --with pyyaml scripts/generate-account-manifests.py --check
```

The generator makes these files:

- Classifier and Drive CronJobs for each account: `cronjob-<nickname>.yaml`
- Weekly Gmail mark-as-read CronJobs for each account: `apps/gmail-classifier/cronjob-<nickname>-mark-read.yaml` (`gmail-mark-read-<nickname>`). The `gmail_mark_read` field sets their schedule
- Symmetrical ExternalSecrets: `secret-primary.yaml`, `secret-secondary.yaml`
- Updated resource lists in `kustomization.yaml`

## Step 5: Verify GitOps Synchronization

Commit the updated matrix and the generated manifests to git. ArgoCD then syncs the resources into the cluster automatically. Run these commands to examine the result:

```bash
# Check ExternalSecret sync status
kubectl -n gmail-classifier get externalsecrets
kubectl -n drive-organizer get externalsecrets

# Check active CronJob schedules
kubectl -n gmail-classifier get cronjobs
kubectl -n drive-organizer get cronjobs
```

Both apps show active schedules. You do not have to do manual steps.

## Step 6: Autonomous Label Discovery for New Accounts

A new Google account can have few or no custom labels. In this case, the classifier does not move valid incoming messages into `ai-review`. Instead, the local LLM finds and creates high-level canonical labels in Gmail on the first match. Examples are `Newsletters`, `Travel`, `Entertainment`, `Shopping`, `Finance`, and `Social`. This behavior needs `ALLOW_LABEL_CREATION=true`. This setting is on by default for all accounts that `scripts/generate-account-manifests.py` generates. Later runs use the new labels again.
