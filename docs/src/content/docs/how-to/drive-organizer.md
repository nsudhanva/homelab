---
title: How to Organize Google Drive with Local AI
description: Deploy and operate the symmetrical Google Drive file organizer with a local Gemma 4 SLM, Firecrawl single-page inspection, and Google Drive Shortcuts.
keywords:
  - google drive organizer
  - local llm document triage
  - pydantic ai drive
  - symmetrical family drive
  - gemma 4 kubernetes
sidebar:
  order: 20
---

# How to Organize Google Drive with Local AI

This guide tells you how to operate, configure, and monitor the automated Google Drive Organizer (`apps/drive-organizer/`).

## Architecture and Workflow

The organizer runs as a daily Kubernetes CronJob at `02:00 UTC` (7:00 PM PDT). It starts one hour after the daily Gmail classifier.

The organizer has these operational characteristics:

- **Entity Symmetrical Hierarchy**: Each family member (`Sudhanva`, `Maanasa`, `Narayana`, `Narmada`, `Rashmi`) has the same subfolder depth (`USA/`, `India/`, `Career/`, `Education/`).
- **Media Pre-Routing**: The organizer sorts photos and videos by date (`Media/YYYY/YYYY-MM/`) from EXIF and Drive metadata. The LLM does not process these files.
- **Document Inspection**: The organizer downloads up to `MAX_DOWNLOAD_BYTES` of each file and extracts the text of the first `PDF_MAX_PAGES` pages. It sends up to `MAX_DOCUMENT_CHARS` characters of this text to the model to find the document type.
- **Pydantic AI**: The organizer uses `pydantic-ai` with structured output models through the shared `homelab-ai` chain.
- **LLM Folder Triage**: If you put a non-taxonomy folder in the root, the model reads the folder manifest (up to `TRIAGE_MAX_FILES` files). It classifies the folder as a code repository or as an unstructured document batch.
- **Code & Project Preservation**: The organizer keeps software projects, git repositories, and Jupyter notebook folders intact. It moves them directly to `Code/<Folder_Name>` or `Colab Notebooks/<Folder_Name>`.
- **Recursive Document Dismantling**: The organizer reads loose document folders recursively. It files each document into the symmetrical taxonomy and uses the folder path as context. Then it removes the empty folders from the bottom up.
- **Joint Drive Shortcuts**: Each joint record (Marriage Certificate, apartment leases, joint tax returns) is in one location only. The organizer automatically makes a native Google Drive Shortcut (`application/vnd.google-apps.shortcut`) in the related folder of the partner.
- **Idempotency**: The organizer tags each processed file with `appProperties.ai_processed = true`. This tag stops a second run from processing the file again.

## Step 1: Examine the Scheduled CronJob

Examine the status and the schedule of the CronJob.

```bash
kubectl -n drive-organizer get cronjob,jobs,pods
```

The schedule must show `0 2 * * *` with `concurrencyPolicy: Forbid`.

## Step 2: Add Loose Files or Folders

You can put items directly in the root of Google Drive (`My Drive`).

- **Loose Files**: The organizer classifies and files single PDFs, images, and documents directly.
- **Unorganized Document Folders**: The organizer automatically reads folders such as `Scans/`, `2024 Taxes/`, and nested folders. The files use the parent folder names as context, which gives high-confidence classification. When all files are moved out, the organizer removes the empty parent folders automatically.
- **Code Repositories**: The model finds folders that contain scripts, software projects, or Jupyter notebooks. The organizer moves these folders intact and does not split them into separate files.
- **Protected Taxonomy**: The root taxonomy directories (`Sudhanva/`, `Maanasa/`, `Code/`, `Media/`, `Review/`) are protected. The organizer never dismantles them.

## Step 3: Trigger an Ad-Hoc Run

To start a run immediately, outside the scheduled cron window, run this command.

```bash
kubectl -n drive-organizer create job --from=cronjob/drive-organizer drive-manual-test
```

To monitor the logs in real time, run this command.

```bash
kubectl -n drive-organizer logs -f job/drive-manual-test
```

## Step 4: Run in Dry-Run Mode

To test the file classification without changes to the files in Google Drive, run this command.

```bash
kubectl -n drive-organizer run drive-dry-run \
  --image=ghcr.io/nsudhanva/homelab-drive-organizer:latest \
  --restart=Never --rm -it \
  --env-from=secret/drive-credentials \
  -- python -m drive_organizer.main --dry-run --limit 10
```

## Step 5: Model Fallback Routing and Provider Toggling

The organizer uses the Pydantic AI `FallbackModel` to keep inference available across local and cloud providers.

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

If a document has a low confidence score or an unclear entity, the classifier moves it to `Review/Needs Review/`. The classifier also sends an alert to the Telegram bot (`@ManassuHomelabBot`).
