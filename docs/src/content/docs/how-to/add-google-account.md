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

All Google accounts are equal peers. There are no hierarchy tiers. Each account has a nickname that describes it. The repository has two accounts today: `personal` and `family`. You manage the account configuration only through Infrastructure as Code (IaC). Do not use manual or ad-hoc workload commands.

## Architecture and Design Principles

The multi-account design follows these principles:

- **Declarative Single Source of Truth**: The file `apps/accounts.yaml` holds the full account matrix for the cluster. The script `scripts/generate-account-manifests.py` makes the symmetrical Kubernetes manifests (`CronJob` and `ExternalSecret`) from this file. The output is the same each time.
- **Fault-Domain & Secret Isolation**: Each account runs in its own non-root Pod and its own CronJob. Each account mounts only its own Kubernetes Secret (`gmail-credentials-<nickname>` and `drive-credentials-<nickname>`), which syncs from the `vault_path` of the account. The `personal` account uses `kv/gmail/credentials`, and the `family` account uses `kv/google/accounts/family`. Use `kv/google/accounts/<nickname>` for new accounts. Thus, one account cannot read the tokens of a different account, and one failure cannot cause more failures.
- **Resource Staggering**: The cron schedules of the accounts start 15 minutes apart (for example, `01:00` for `personal` Gmail and `01:15` for `family` Gmail). Thus, the runs of the accounts do not overlap in time or compete for the same API rate limits.
- **Notification Routing**: Each notification has a header badge for its account (`[Personal]`, `[Family]`). As an option, it can go to a different Telegram forum topic through `TELEGRAM_TOPIC_ID`.

## Step 1: Get Google OAuth Credentials

In the Google Cloud Console, create an OAuth 2.0 Client for the target Google account:

- Go to the Google Cloud Console APIs & Services Credentials page.
- Create an OAuth Client ID with the application type **Desktop app**.
- Make sure that these necessary scopes are enabled:
  - Gmail Classifier: `https://www.googleapis.com/auth/gmail.modify`
  - Drive Organizer: `https://www.googleapis.com/auth/drive`
- Run `uv run scripts/get-google-oauth-token.py --account <nickname>` to make the initial `refresh_token`. The script asks for one token with both scopes, so Gmail and Drive share the same credentials. It reads `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from the environment, or asks for them.

## Step 2: Store Credentials in HashiCorp Vault

Never commit credentials to git. Put the credentials in HashiCorp Vault under the path for the new account. This example adds an account with the nickname `work`:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/google/accounts/work \
  client_id="REPLACE_ME" \
  client_secret="REPLACE_ME" \
  refresh_token="REPLACE_ME"
```

All accounts share the Telegram bot token at `kv/telegram/bot` (property `token`). If that path already exists, do not write it again.

## Step 3: Declare Accounts in the Account Matrix

Add the account entry to `apps/accounts.yaml` with its nickname. `vault_path` has no `kv/` prefix. Give the new account the next free 15-minute slot:

```yaml
accounts:
  - nickname: personal
    schedule:
      gmail: "0 1 * * *"
      gmail_mark_read: "0 4 * * 0"
      drive: "0 2 * * *"
    vault_path: gmail/credentials
  - nickname: family
    schedule:
      gmail: "15 1 * * *"
      gmail_mark_read: "15 4 * * 0"
      drive: "15 2 * * *"
    vault_path: google/accounts/family
  - nickname: work
    schedule:
      gmail: "30 1 * * *"
      gmail_mark_read: "30 4 * * 0"
      drive: "30 2 * * *"
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

- Classifier and Drive CronJobs for each account: `cronjob-<nickname>.yaml` in `apps/gmail-classifier/` and `apps/drive-organizer/`
- Weekly Gmail mark-as-read CronJobs for each account: `apps/gmail-classifier/cronjob-<nickname>-mark-read.yaml` (`gmail-mark-read-<nickname>`). The `gmail_mark_read` field sets their schedule
- ExternalSecrets for each account: `secret-<nickname>.yaml` in both app directories (`gmail-credentials-<nickname>` and `drive-credentials-<nickname>`)
- Updated resource lists in `kustomization.yaml`

The generator deletes `cronjob-*.yaml` and `secret-*.yaml` files that no longer match an account in `apps/accounts.yaml`.

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

A new Google account can have few or no custom labels. In this case, the classifier does not move valid incoming messages into `ai-review`. Instead, the prompt asks the model to propose one broad Title Case label, such as `Travel` or `Education`, and the classifier creates it in Gmail. The code accepts a new label only if it is at most 40 characters and does not start with `CATEGORY_`. This behavior needs `ALLOW_LABEL_CREATION=true`. This setting is on by default for all accounts that `scripts/generate-account-manifests.py` generates. Later runs use the new labels again.
