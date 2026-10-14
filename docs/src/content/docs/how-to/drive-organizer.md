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
- **Firecrawl Single-Page Inspection**: The organizer streams only the first page of a PDF (or up to 2,000 characters). It uses this text to find the document type and reading order, and does not download the full file.
- **Pydantic AI & Local Inference**: The organizer uses `pydantic-ai` with structured output models. These models point to `llama-server.llama.svc.cluster.local:8080/v1`, which runs Google Gemma 4 (E2B).
- **LLM Folder Triage**: If you put a non-taxonomy folder in the root, Gemma reads the folder manifest. It classifies the folder as a code repository or as an unstructured document batch.
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
- **Code Repositories**: The local LLM finds folders that contain scripts, software projects, or Jupyter notebooks. The organizer moves these folders intact and does not split them into separate files.
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

- **Primary Model**: The default is the local Google Gemma 4 E2B model (`http://llama-server.llama.svc.cluster.local:8080/v1`).
- **Fallback Model**: If the local server has connection drops, timeouts, or OOM errors, the organizer sends requests to OpenRouter Google Gemma 4 31B (`google/gemma-4-31b-it`).
- **Zero-Secret Vault Integration**: HashiCorp Vault keeps the OpenRouter API key at `kv/openrouter` (`api_key`). A Kubernetes `ExternalSecret` syncs the key into `openrouter-credentials`.

### Add the OpenRouter Key to Vault

Before you enable the OpenRouter fallback in a new cluster environment, write the API key to Vault.

```bash
vault kv put kv/openrouter api_key="sk-or-v1-xxxxxxxxxxxxxxxx"
```

### Change the Default Model

To change between local inference and OpenRouter without a container rebuild, change `PRIMARY_LLM_PROVIDER` and `FALLBACK_LLM_PROVIDER` in `apps/drive-organizer/cronjob.yaml`.

```yaml
            env:
            - name: PRIMARY_LLM_PROVIDER
              value: "openrouter"
            - name: FALLBACK_LLM_PROVIDER
              value: "local"
```

You can also change the provider at runtime with `kubectl`.

```bash
# Make OpenRouter Gemma 4 31B primary
kubectl -n drive-organizer set env cronjob/drive-organizer PRIMARY_LLM_PROVIDER=openrouter FALLBACK_LLM_PROVIDER=local

# Revert to local SLM as primary
kubectl -n drive-organizer set env cronjob/drive-organizer PRIMARY_LLM_PROVIDER=local FALLBACK_LLM_PROVIDER=openrouter

# Disable fallback entirely (offline mode)
kubectl -n drive-organizer set env cronjob/drive-organizer FALLBACK_LLM_PROVIDER=none
```

## Step 6: Review Quarantined Files

If a document has a low confidence score or an unclear entity, the classifier moves it to `Review/Needs Review/`. The classifier also sends an alert to the Telegram bot (`@ManassuHomelabBot`).
