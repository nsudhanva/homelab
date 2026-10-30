---
title: How to Organize Google Drive with AI
description: Deploy and operate the symmetrical Google Drive file organizer with the homelab-ai model chain, document text inspection, and joint document copies.
keywords:
  - google drive organizer
  - llm document triage
  - pydantic ai drive
  - symmetrical family drive
  - claude haiku
sidebar:
  order: 20
---

# How to Organize Google Drive with AI

This guide tells you how to operate, configure, and monitor the automated Google Drive Organizer (`apps/drive-organizer/`).

## Architecture and Workflow

The organizer runs as one daily Kubernetes CronJob per Google account. The schedules come from `apps/accounts.yaml`:

| CronJob | Schedule | Secret |
| --- | --- | --- |
| `drive-organizer-personal` | `0 2 * * *` (02:00) | `drive-credentials-personal` |
| `drive-organizer-family` | `15 2 * * *` (02:15) | `drive-credentials-family` |

Each job starts one hour after the Gmail classifier of the same account. Both run with `--scope=root`, so they process only items in the root of `My Drive`.

The organizer has these operational characteristics:

- **Entity Symmetrical Hierarchy**: Each family member (`Sudhanva`, `Maanasa`, `Narayana`, `Narmada`, `Rashmi`) has the same subfolder depth (`USA/`, `India/`, `Career/`, `Education/`).
- **Media Pre-Routing**: The organizer sorts photos and videos by date (`Media/YYYY/YYYY-MM/`) from EXIF and Drive metadata. The LLM does not process these files.
- **Document Inspection**: The organizer downloads up to `MAX_DOWNLOAD_BYTES` of each file and extracts the text of the first `PDF_MAX_PAGES` pages. It sends up to `MAX_DOCUMENT_CHARS` characters of this text to the model to find the document type.
- **Pydantic AI**: The organizer uses `pydantic-ai` with structured output models through the shared `homelab-ai` chain.
- **LLM Folder Triage**: If you put a non-taxonomy folder in the root, the model reads the folder manifest (up to `TRIAGE_MAX_FILES` files). It classifies the folder as a code repository or as an unstructured document batch.
- **Code & Project Preservation**: The organizer keeps software projects, git repositories, and Jupyter notebook folders intact. It moves them directly to `Code/<Folder_Name>` or `Colab Notebooks/<Folder_Name>`.
- **Recursive Document Dismantling**: The organizer reads loose document folders recursively. It files each document into the symmetrical taxonomy and uses the folder path as context. Then it removes the empty folders from the bottom up.
- **Joint Document Copies**: When the model marks a document as joint (Marriage Certificate, apartment leases, joint tax returns) and the owner is `Sudhanva` or `Maanasa`, the organizer files the original under the owner. It then makes a full copy of the file (`copy_file`) in the same path under the spouse folder. The Telegram summary counts these as `Joint Copies Created`.
- **Idempotency**: The organizer tags each processed file with `appProperties.ai_processed = true`. This tag stops a second run from processing the file again.

## Step 1: Examine the Scheduled CronJob

Examine the status and the schedule of the CronJobs.

```bash
kubectl -n drive-organizer get cronjob,jobs,pods
```

The schedules must show `0 2 * * *` for `drive-organizer-personal` and `15 2 * * *` for `drive-organizer-family`. Both use `concurrencyPolicy: Forbid`.

## Step 2: Add Loose Files or Folders

You can put items directly in the root of Google Drive (`My Drive`).

- **Loose Files**: The organizer classifies and files single PDFs, images, and documents directly.
- **Unorganized Document Folders**: The organizer automatically reads folders such as `Scans/`, `2024 Taxes/`, and nested folders. The files use the parent folder names as context, which gives high-confidence classification. When all files are moved out, the organizer removes the empty parent folders automatically.
- **Code Repositories**: The model finds folders that contain scripts, software projects, or Jupyter notebooks. The organizer moves these folders intact and does not split them into separate files.
- **Protected Taxonomy**: The root folders in `PROTECTED_ROOT_FOLDERS` (`apps/drive-organizer/src/drive_organizer/drive_client.py`) are protected. They are `Sudhanva`, `Maanasa`, `Narayana`, `Narmada`, `Rashmi`, `Media`, `Books`, `CVs`, `Colab Notebooks`, `Google AI Studio`, `Models`, `Code`, and `Review` (matched without regard to case). The organizer never dismantles them.

## Step 3: Trigger an Ad-Hoc Run

To start a run immediately, outside the scheduled cron window, run this command. Use `drive-organizer-family` for the second account.

```bash
kubectl -n drive-organizer create job --from=cronjob/drive-organizer-personal drive-manual-test
```

To monitor the logs in real time, run this command.

```bash
kubectl -n drive-organizer logs -f job/drive-manual-test
```

## Step 4: Run in Dry-Run Mode

The CronJob always runs a real pass. To test the file classification without changes to the files in Google Drive, run the app from your workstation with `--dry-run`. The app reads `DRIVE_CLIENT_ID`, `DRIVE_CLIENT_SECRET`, and `DRIVE_REFRESH_TOKEN` from the environment or from a `.env` file in the app directory. Take the values from the Vault path of the account (`kv/gmail/credentials` for `personal`, `kv/google/accounts/family` for `family`).

```bash
cd apps/drive-organizer
uv run python -m drive_organizer.main --dry-run --limit 10
```

The app also accepts `--scope root|all` (default `root`), `--all` (same as `--scope=all`), and `--account <nickname>`.

## Step 5: Model Fallback Routing and Provider Toggling

The organizer uses the Pydantic AI `FallbackModel` through `homelab-ai` to keep inference available across cloud and local providers. File text goes to Anthropic first.

- **Model chain**: The organizer uses the shared `homelab-ai` chain. The default is Anthropic `claude-haiku-5-5`, then OpenRouter `google/gemma-4-31b-it`, then the local `gemma-4-e2b-it` model.
- **Secrets**: The `homelab-ai-credentials` ExternalSecret reads the OpenRouter and Anthropic keys from Vault (`kv/openrouter`, `kv/anthropic`).

### Change the model

Change models in Git, not with `kubectl`. To change the model for every AI workload, edit `packages/homelab-ai/kustomize/kustomization.yaml`. To change it for the organizer only, add an `env` entry to `apps/drive-organizer/cronjob-personal.yaml` and `apps/drive-organizer/cronjob-family.yaml`:

```yaml
            env:
            - name: AI_MODEL
              value: "local:gemma-4-e2b-it"
```

For all settings, see [AI Configuration Reference](/reference/ai-configuration/).

## Step 6: Review Quarantined Files

If a document has a low confidence score or an unclear entity, the classifier moves it to `Review/Needs Review/`. At the end of each run, the organizer sends one summary to Telegram. The `Needs Review` line shows how many files went to review in that run.
