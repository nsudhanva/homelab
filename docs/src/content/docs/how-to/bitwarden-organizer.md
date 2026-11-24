---
title: How to Organize Bitwarden Items with AI
description: Configure, run, and monitor the Bitwarden organizer, a daily CronJob that files Bitwarden items without a folder into the existing folders with the homelab-ai model chain.
keywords:
  - bitwarden organizer
  - bitwarden cli kubernetes
  - bitwarden folders ai
  - pydantic ai bitwarden
  - claude haiku
---

This guide tells how to configure, run, and monitor the Bitwarden organizer (`apps/bitwarden-organizer/`).

## Architecture and Workflow

The organizer runs as one Kubernetes CronJob, `bitwarden-organizer`, each day at 02:00 (`0 2 * * *`). The CronJob uses `concurrencyPolicy: Forbid`.

The organizer has these behaviors:

- Bitwarden CLI: The image contains the official Bitwarden CLI (`bw`). The `Dockerfile` pins the version and the SHA-256 checksum of the release archive.
- Login: The organizer logs in with the personal API key (`bw login --apikey`). It unlocks the vault with the master password (`bw unlock --passwordenv`). It gives the credentials to `bw` through environment variables and the item data through standard input. Neither shows in the process arguments. It locks the vault at the end of each run.
- Scope: The organizer processes only active items that have no folder. It does not change items that are in a folder.
- Examples: For each folder, the model gets up to `EXAMPLES_PER_FOLDER` items that are already in the folder. The model uses these examples to learn the filing habits of the owner.
- Data sent to the model: The item name, the item type, the website hosts, the email domain of the username, and the card brand. The organizer does not send passwords, notes, custom field values, card numbers, or the local part of the username.
- Model chain: The organizer uses the shared `homelab-ai` chain. The default is Anthropic `claude-haiku-5-5`, then OpenRouter `google/gemma-4-31b-it`, then the local `gemma-4-e2b-it` model.
- Folders: The model must choose one of the existing folders. The organizer does not create folders. If the model gives a folder that does not exist, the organizer skips the item.
- Low confidence: The organizer moves each item to the chosen folder, also when the confidence is low. The Telegram summary lists the items with a confidence below `CONFIDENCE_THRESHOLD`, so that you can examine them.
- Model outage: If no model answers, the organizer stops, locks the vault, and exits with an error. Kubernetes then retries the job.
- Summary: The organizer sends a Telegram summary when a run finds items without a folder or stops with an error.

## Step 1: Store the Credentials in Vault

The organizer needs the Bitwarden personal API key and the master password.

Get the API key in the Bitwarden web vault: **Settings** > **Security** > **Keys** > **View API key**.

Write the values to Vault. Run the command in your own terminal. The command asks for each value and hides the input, so the values do not go into the shell history:

```bash
kubectl -n vault exec -it vault-0 -- sh -c 'read -r -s -p "client_id: " ID; echo; read -r -s -p "client_secret: " SECRET; echo; read -r -s -p "master_password: " PW; echo; vault kv put kv/bitwarden/automation client_id="$ID" client_secret="$SECRET" master_password="$PW"'
```

The `bitwarden-credentials` ExternalSecret (`apps/bitwarden-organizer/secret.yaml`) reads `kv/bitwarden/automation` and `kv/telegram/bot`.

Make sure that External Secrets Operator created the Secret:

```bash
kubectl -n bitwarden-organizer get externalsecret,secret
```

:::caution
The path `kv/bitwarden/automation` gives full access to the Bitwarden vault. Do not give other workloads access to this path.
:::

## Step 2: Examine the CronJob

```bash
kubectl -n bitwarden-organizer get cronjob,jobs,pods
```

## Step 3: Start a Manual Run

To start a run outside the schedule, run this command:

```bash
kubectl -n bitwarden-organizer create job --from=cronjob/bitwarden-organizer bitwarden-manual-test
```

To follow the logs, run this command:

```bash
kubectl -n bitwarden-organizer logs -f job/bitwarden-manual-test
```

The log shows one line for each item, with the item name, the folder, and the confidence. It does not show secrets.

## Step 4: Run in Dry-Run Mode

The CronJob always changes Bitwarden. To test the classification without changes, run the app from your workstation with `--dry-run`. Install the Bitwarden CLI and put `BW_CLIENTID`, `BW_CLIENTSECRET`, and `BW_PASSWORD` in a `.env` file in `apps/bitwarden-organizer/`. Do not commit the file.

```bash
cd apps/bitwarden-organizer
uv run python -m bitwarden_organizer.main --dry-run --limit 10
```

## Step 5: Change the Settings

Change the `env` entries in `apps/bitwarden-organizer/cronjob.yaml`, then push to Git:

| Variable | Default | Description |
| --- | --- | --- |
| `CONFIDENCE_THRESHOLD` | `0.80` | The summary lists filed items below this value for review |
| `EXAMPLES_PER_FOLDER` | `20` | Filed items that the model sees for each folder |
| `MAX_ITEMS` | `200` | Maximum number of items to file in one run |
| `BW_SERVER` | `bw` default (`bitwarden.com`) | Bitwarden server URL |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `bw login failed` | The API key in Vault is wrong, or you rotated the key | Get a new API key and write it to `kv/bitwarden/automation` |
| `bw unlock failed` | The master password in Vault is wrong | Write the current master password to `kv/bitwarden/automation` |
| `CreateContainerConfigError` | The `bitwarden-credentials` Secret does not exist | Do Step 1, then examine the ExternalSecret status |
| `Run stopped: No model answered` | No model in the `homelab-ai` chain answered | Run `uv run homelab-ai ping`. Refer to [AI Configuration Reference](/reference/ai-configuration/) |
