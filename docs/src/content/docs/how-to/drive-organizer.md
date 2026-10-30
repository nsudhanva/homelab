---
title: How to Organize Google Drive with AI
description: Run and configure the Google Drive file organizer, which uses the homelab-ai model chain, reads document text, and makes copies of joint documents.
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

This guide tells how to run, configure, and monitor the Google Drive Organizer (`apps/drive-organizer/`).

## Architecture and Workflow

The organizer runs as one daily Kubernetes CronJob for each Google account. The schedules come from `apps/accounts.yaml`.

| CronJob | Schedule | Secret |
| --- | --- | --- |
| `drive-organizer-personal` | `0 2 * * *` (02:00) | `drive-credentials-personal` |
| `drive-organizer-family` | `15 2 * * *` (02:15) | `drive-credentials-family` |

Each job starts one hour after the Gmail classifier of the same account. The two jobs run with `--scope=root`, so they process only the items in the root of `My Drive`.

The organizer has these behaviors:

- Symmetrical hierarchy: Each family member (`Sudhanva`, `Maanasa`, `Narayana`, `Narmada`, `Rashmi`) has the same subfolders (`USA/`, `India/`, `Career/`, `Education/`).
- Media routing: The organizer sorts photos and videos by date into `Media/YYYY/YYYY-MM/`. It reads the date from EXIF and Drive metadata. The LLM does not process these files.
- Document inspection: The organizer downloads up to `MAX_DOWNLOAD_BYTES` of each file and extracts the text of the first `PDF_MAX_PAGES` pages. It sends up to `MAX_DOCUMENT_CHARS` characters of this text to the model to find the document type.
- Pydantic AI: The organizer uses `pydantic-ai` with structured output models through the shared `homelab-ai` chain.
- Folder triage: A root folder can be outside the taxonomy. For such a folder, the model reads the folder manifest (up to `TRIAGE_MAX_FILES` files). It classifies the folder as a code repository or as a batch of unstructured documents.
- Code folders: The organizer keeps software projects, Git repositories, and Jupyter notebook folders intact. It moves them to `Code/<Folder_Name>` or `Colab Notebooks/<Folder_Name>`.
- Document folders: The organizer reads loose document folders recursively. It files each document into the taxonomy and uses the folder path as context. Then it removes the empty folders from the bottom up.
- Joint document copies: A document can be joint, for example a marriage certificate, an apartment lease, or a joint tax return. If the owner is `Sudhanva` or `Maanasa`, the organizer files the original under the owner. It then copies the file (`copy_file`) to the same path under the spouse folder. The Telegram summary counts these copies as `Joint Copies Created`.
- Idempotency: The organizer tags each processed file with `appProperties.ai_processed = true`. The next runs skip files that have this tag.

## Step 1: Examine the CronJobs

Examine the status and the schedule of the CronJobs:

```bash
kubectl -n drive-organizer get cronjob,jobs,pods
```

The schedule of `drive-organizer-personal` is `0 2 * * *`, and the schedule of `drive-organizer-family` is `15 2 * * *`. The two CronJobs use `concurrencyPolicy: Forbid`.

## Step 2: Add Loose Files or Folders

Put items in the root of Google Drive (`My Drive`). The organizer handles them as follows:

- Loose files: The organizer classifies and files single PDFs, images, and documents.
- Document folders: The organizer reads folders such as `Scans/`, `2024 Taxes/`, and their subfolders. The parent folder names give context to the classification. After it moves all files out, the organizer removes the empty parent folders.
- Code repositories: The model finds folders that contain scripts, software projects, or Jupyter notebooks. The organizer moves each of these folders as one unit.
- Protected taxonomy: The organizer does not dismantle the root folders in `PROTECTED_ROOT_FOLDERS` (`apps/drive-organizer/src/drive_organizer/drive_client.py`). These folders are `Sudhanva`, `Maanasa`, `Narayana`, `Narmada`, `Rashmi`, `Media`, `Books`, `CVs`, `Colab Notebooks`, `Google AI Studio`, `Models`, `Code`, and `Review`. The match ignores case.

## Step 3: Start a Manual Run

To start a run outside the schedule, run this command. Use `drive-organizer-family` for the second account.

```bash
kubectl -n drive-organizer create job --from=cronjob/drive-organizer-personal drive-manual-test
```

To follow the logs, run this command:

```bash
kubectl -n drive-organizer logs -f job/drive-manual-test
```

## Step 4: Run in Dry-Run Mode

The CronJob always changes the files in Google Drive. To test the classification without changes, run the app from your workstation with `--dry-run`.

The app reads `DRIVE_CLIENT_ID`, `DRIVE_CLIENT_SECRET`, and `DRIVE_REFRESH_TOKEN` from the environment or from a `.env` file in the app directory. Get the values from the Vault path of the account: `kv/gmail/credentials` for `personal` and `kv/google/accounts/family` for `family`.

```bash
cd apps/drive-organizer
uv run python -m drive_organizer.main --dry-run --limit 10
```

The app also accepts `--scope root|all` (default `root`), `--all` (the same as `--scope=all`), and `--account <nickname>`.

## Step 5: Configure the Model Fallback

The organizer uses the Pydantic AI `FallbackModel` through `homelab-ai`. If one provider is not available, the next provider in the chain answers. File text goes to Anthropic first.

- Model chain: The organizer uses the shared `homelab-ai` chain. The default is Anthropic `claude-haiku-5-5`, then OpenRouter `google/gemma-4-31b-it`, then the local `gemma-4-e2b-it` model.
- Secrets: The `homelab-ai-credentials` ExternalSecret reads the OpenRouter and Anthropic keys from Vault (`kv/openrouter`, `kv/anthropic`).

### Change the model

Change the model in Git. Do not change it with `kubectl`. To change the model for all AI workloads, edit `packages/homelab-ai/kustomize/kustomization.yaml`. To change it for the organizer only, add an `AI_MODEL` entry to the `env` list in `generate_drive_cronjob` of `scripts/generate-account-manifests.py`. Then run the generator, as in [How to Add a Google Account](/how-to/add-google-account/). The generator writes the entry to `apps/drive-organizer/cronjob-personal.yaml` and `apps/drive-organizer/cronjob-family.yaml`. Do not edit these files directly, because the generator overwrites them.

```yaml
            env:
            - name: AI_MODEL
              value: "local:gemma-4-e2b-it"
```

For all settings, see [AI Configuration Reference](/reference/ai-configuration/).

## Step 6: Review Quarantined Files

If a document has a low confidence score or an unclear owner, the classifier moves it to `Review/Needs Review/`. At the end of each run, the organizer sends one summary to Telegram. The `Needs Review` line shows the number of files that went to review in that run.
