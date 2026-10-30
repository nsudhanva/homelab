---
title: How to Add a Google Account to the AI Workloads
description: Add a Google account to Gmail Classifier and Drive Organizer through the account matrix in apps/accounts.yaml, Vault, and ArgoCD.
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

This guide adds a Google account to the AI workloads `apps/gmail-classifier` and `apps/drive-organizer`. You declare the account in a file, keep its credentials in Vault, and let ArgoCD deploy it.

Each account has a nickname, and all accounts have the same configuration. The repository has two accounts: `personal` and `family`. Change the account configuration only through the files in Git. Do not create or change account workloads with `kubectl`.

## Architecture

The accounts use this design:

- Single source of truth: `apps/accounts.yaml` holds the account matrix for the cluster. The script `scripts/generate-account-manifests.py` generates the CronJob and ExternalSecret manifests from this file. The output is the same on each run.
- Secret isolation: Each account runs in its own non-root pod and its own CronJob. Each account mounts only its own Secrets, `gmail-credentials-<nickname>` and `drive-credentials-<nickname>`. These Secrets sync from the `vault_path` of the account.
- Vault paths: The `personal` account uses `kv/gmail/credentials`, and the `family` account uses `kv/google/accounts/family`. Use `kv/google/accounts/<nickname>` for a new account. One account cannot read the tokens of a different account, and a failure in one account does not stop the other accounts.
- Staggered schedules: The schedules of the accounts start 15 minutes apart. For example, Gmail runs at `01:00` for `personal` and at `01:15` for `family`. The runs do not overlap and do not compete for the same API rate limits.
- Notifications: Each notification has a header badge for its account (`[Personal]`, `[Family]`). As an option, `TELEGRAM_TOPIC_ID` sends the notifications of an account to a different Telegram forum topic.

## Step 1: Get Google OAuth Credentials

In the Google Cloud Console, create an OAuth 2.0 client for the Google account:

- Go to the Google Cloud Console APIs & Services Credentials page.
- Create an OAuth client ID with the application type **Desktop app**.
- Make sure that these scopes are enabled:
  - Gmail Classifier: `https://www.googleapis.com/auth/gmail.modify`
  - Drive Organizer: `https://www.googleapis.com/auth/drive`
- Run `uv run scripts/get-google-oauth-token.py --account <nickname>` to get the first `refresh_token`.

The script requests one token with the two scopes, so Gmail and Drive share the same credentials. It reads `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from the environment. If these variables are not set, it asks for the values.

## Step 2: Store the Credentials in Vault

Do not commit credentials to Git. Put the credentials in Vault under the path of the new account. This example adds an account with the nickname `work`:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/google/accounts/work \
  client_id="REPLACE_ME" \
  client_secret="REPLACE_ME" \
  refresh_token="REPLACE_ME"
```

All accounts share the Telegram bot token at `kv/telegram/bot` (property `token`). If that path exists, do not write it again.

## Step 3: Add the Account to the Account Matrix

Add the account entry to `apps/accounts.yaml` with its nickname. Write `vault_path` without the `kv/` prefix. Give the new account the next free 15-minute slot:

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

## Step 4: Generate the Manifests

Run the generator script:

```bash
uv run --with pyyaml scripts/generate-account-manifests.py
```

To make sure that the manifests in Git agree with `apps/accounts.yaml`, run the check mode. This mode does not write files.

```bash
uv run --with pyyaml scripts/generate-account-manifests.py --check
```

The generator writes these files:

- Gmail and Drive CronJobs for each account: `cronjob-<nickname>.yaml` in `apps/gmail-classifier/` and `apps/drive-organizer/`
- Weekly Gmail mark-as-read CronJobs for each account: `apps/gmail-classifier/cronjob-<nickname>-mark-read.yaml` (`gmail-mark-read-<nickname>`). The `gmail_mark_read` field sets their schedule.
- ExternalSecrets for each account: `secret-<nickname>.yaml` in the two app directories (`gmail-credentials-<nickname>` and `drive-credentials-<nickname>`)
- The resource lists in `kustomization.yaml`

The generator deletes each `cronjob-*.yaml` and `secret-*.yaml` file that does not match an account in `apps/accounts.yaml`.

## Step 5: Verify the Sync

Commit the account matrix and the generated manifests to Git. ArgoCD syncs the resources to the cluster. Run these commands to examine the result:

```bash
# Check ExternalSecret sync status
kubectl -n gmail-classifier get externalsecrets
kubectl -n drive-organizer get externalsecrets

# Check active CronJob schedules
kubectl -n gmail-classifier get cronjobs
kubectl -n drive-organizer get cronjobs
```

The two apps show a CronJob for the new account. No manual steps are necessary.

## Label Discovery for New Accounts

A new Google account can have few or no custom labels. For a valid message that fits no existing label, the model proposes one broad Title Case label, such as `Travel` or `Education`. The classifier creates that label in Gmail and does not move the message to `ai-review`. The classifier accepts a new label only if it has 40 characters or fewer and does not start with `CATEGORY_`. Later runs use the new labels.

This behavior needs `ALLOW_LABEL_CREATION=true`. `scripts/generate-account-manifests.py` sets this value for all accounts.
