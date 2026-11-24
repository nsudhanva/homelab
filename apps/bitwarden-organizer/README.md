# Bitwarden Organizer

A daily AI job that files Bitwarden items that have no folder into the existing folders. It runs as a Kubernetes CronJob.

## Overview

- Logs in to Bitwarden with the `bw` CLI, a personal API key, and the master password from Vault (`kv/bitwarden/automation`).
- Finds the active items that have no folder.
- Shows the model each folder with up to `EXAMPLES_PER_FOLDER` items that are already in it, so that the model learns the filing habits of the owner.
- Sends only the item name, the item type, the website hosts, the email domain of the username, and the card brand to the model. It does not send passwords, notes, custom field values, or card numbers.
- Classifies each item with the shared `homelab-ai` model chain (Claude Haiku 5.5 first). The model must choose one of the existing folders. The job does not create folders.
- Moves each item to the chosen folder, also when the confidence is low. The Telegram summary lists the items with a confidence below `CONFIDENCE_THRESHOLD`.
- Skips an item when the model gives a folder that does not exist.
- Locks the vault at the end of each run.
- Runs one CronJob, `bitwarden-organizer`, at 02:00 `America/Los_Angeles`.
- Sends a Telegram summary when a run finds items without a folder or stops with an error.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BW_CLIENTID` | | Personal API key `client_id`, from Vault |
| `BW_CLIENTSECRET` | | Personal API key `client_secret`, from Vault |
| `BW_PASSWORD` | | Master password, from Vault |
| `BW_SERVER` | `bw` default (`bitwarden.com`) | Bitwarden server URL |
| `BITWARDENCLI_APPDATA_DIR` | `/tmp/bitwarden` | Writable directory for the `bw` state |
| `BW_TIMEOUT_SECONDS` | `180` | Timeout for one `bw` command |
| `EXAMPLES_PER_FOLDER` | `20` | Filed items that the model sees for each folder |
| `MAX_ITEMS` | `200` | Maximum number of items to file in one run |
| `CONFIDENCE_THRESHOLD` | `0.80` | The summary lists filed items below this value for review |
| `TELEGRAM_BOT_TOKEN` | | Telegram bot token, from Vault |
| `TELEGRAM_CHAT_ID` | `7341944813` | Telegram chat for the summary |

## Local Run

The job needs the `bw` CLI on `PATH`. Put the three `BW_*` credentials in the environment or in a `.env` file in this directory. Do not commit the file.

```bash
cd apps/bitwarden-organizer
uv run python -m bitwarden_organizer.main --dry-run --limit 10
```

## Checks

```bash
uv run ruff check && uv run ruff format --check && uv run ty check && uv run pytest
```

Refer to `docs/src/content/docs/how-to/bitwarden-organizer.md`.
