---
title: How to Add Multiple Google Accounts
description: Configure, securely store, and deploy multiple isolated Google accounts (personal and family) for Gmail Classifier and Drive Organizer via GitOps and HashiCorp Vault.
keywords:
  - multi-account google
  - gmail classifier family
  - drive organizer multi-account
  - vault google oauth
  - kubernetes cronjob gitops
sidebar:
  order: 21
---

# How to Add Multiple Google Accounts

This problem-oriented guide explains how to configure, store secrets for, and operate multiple Google accounts (such as `personal` and `family`) across the homelab AI pipeline (`apps/gmail-classifier` and `apps/drive-organizer`).

## Architectural Isolation Model

To guarantee strict security boundaries and system resilience, accounts are isolated according to Senior Staff SWE principles:

- **Fault-Domain Isolation**: Monolithic loops across accounts are strictly avoided. Each account executes in a dedicated Pod and CronJob (`gmail-classifier` for personal, `gmail-classifier-family` for family).
- **Least-Privilege Secret Isolation**: Each account mounts its own dedicated Kubernetes Secret (`gmail-credentials` vs `gmail-credentials-family`) synchronized from isolated paths in HashiCorp Vault. The family account pod never has access to personal OAuth tokens, and vice versa.
- **Independent Failure Domains**: A token revocation or rate limit on one account never blocks or impacts the execution of another account.
- **Resource Staggering**: Cron schedules are staggered by fifteen minutes (`01:00 UTC` for personal Gmail, `01:15 UTC` for family Gmail; `02:00 UTC` for personal Drive, `02:15 UTC` for family Drive) to prevent GPU slot contention on the local Gemma 4 LLM server (`llama-server`).
- **Telegram Routing & Badging**: Notifications include account-specific badges (`[Personal]` or `[Family]`) and optionally target distinct Telegram forum topics via `TELEGRAM_TOPIC_ID`.

## Step 1: Obtain Google OAuth Credentials

Create an OAuth 2.0 Client in the Google Cloud Console for the target account:

- Navigate to the Google Cloud Console APIs & Services Credentials page.
- Create an OAuth Client ID with application type **Desktop app**.
- Ensure the following scopes are enabled:
  - For Gmail Classifier: `https://www.googleapis.com/auth/gmail.modify`
  - For Drive Organizer: `https://www.googleapis.com/auth/drive`
- Generate an authorization code and exchange it for a long-lived `refresh_token`.

## Step 2: Store Credentials in HashiCorp Vault

All sensitive OAuth credentials are stored in HashiCorp Vault and synchronized into Kubernetes via the External Secrets Operator. Never commit plain-text credentials or `.env` files to git.

Log into Vault and write the credentials for the personal and family accounts:

```bash
# Personal account credentials
vault kv put kv/gmail/credentials \
  client_id="YOUR_PERSONAL_CLIENT_ID" \
  client_secret="YOUR_PERSONAL_CLIENT_SECRET" \
  refresh_token="YOUR_PERSONAL_REFRESH_TOKEN"

# Family account credentials
vault kv put kv/gmail/family \
  client_id="YOUR_FAMILY_CLIENT_ID" \
  client_secret="YOUR_FAMILY_CLIENT_SECRET" \
  refresh_token="YOUR_FAMILY_REFRESH_TOKEN"

# Shared Telegram notification credentials
vault kv put kv/telegram/bot \
  token="YOUR_TELEGRAM_BOT_TOKEN"
```

## Step 3: Verify ExternalSecrets Synchronization

The GitOps repository defines `ExternalSecret` manifests (`secret.yaml` and `secret-family.yaml`) in each application directory. Once ArgoCD synchronizes the repository, verify that the Kubernetes secrets have been generated:

```bash
# Check ExternalSecret synchronization status in gmail-classifier
kubectl -n gmail-classifier get externalsecret,secret

# Check ExternalSecret synchronization status in drive-organizer
kubectl -n drive-organizer get externalsecret,secret
```

Each ExternalSecret should report `STATUS: SecretSynced` with a matching secret name.

## Step 4: Verify CronJob Configurations

List the active CronJobs to verify that both personal and family accounts are configured with staggered schedules:

```bash
# Gmail Classifier CronJobs
kubectl -n gmail-classifier get cronjobs

# Drive Organizer CronJobs
kubectl -n drive-organizer get cronjobs
```

Expected output confirms the schedules:

- `gmail-classifier`: `0 1 * * *` (`ACCOUNT_NAME: personal`)
- `gmail-classifier-family`: `15 1 * * *` (`ACCOUNT_NAME: family`)
- `drive-organizer`: `0 2 * * *` (`ACCOUNT_NAME: personal`)
- `drive-organizer-family`: `15 2 * * *` (`ACCOUNT_NAME: family`)

## Step 5: Trigger Ad-Hoc Test Runs

Trigger a manual test job for each family account pipeline to verify authentication, inference, and Telegram dispatch:

```bash
# Trigger Gmail Classifier test job for family account
kubectl -n gmail-classifier create job --from=cronjob/gmail-classifier-family test-gmail-family

# Monitor the logs
kubectl -n gmail-classifier logs -f job/test-gmail-family

# Trigger Drive Organizer test job for family account
kubectl -n drive-organizer create job --from=cronjob/drive-organizer-family test-drive-family

# Monitor the logs
kubectl -n drive-organizer logs -f job/test-drive-family
```

Inspect the log output to confirm:

- Log lines are tagged with `[family]`.
- Messages dispatched to Telegram display the `[Family]` header badge.
- When finished, clean up the test jobs:

```bash
kubectl -n gmail-classifier delete job test-gmail-family
kubectl -n drive-organizer delete job test-drive-family
```
