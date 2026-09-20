---
title: How to Organize Google Drive with Local AI
description: Deploy and operate the symmetrical Google Drive file organizer using local Gemma 4 SLM, Firecrawl single-page inspection, and Google Drive Shortcuts.
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

This problem-oriented guide explains how to operate, configure, and monitor the automated Google Drive Organizer (`apps/drive-organizer/`).

## Architecture and Workflow

The organizer runs as a daily Kubernetes CronJob scheduled at `02:00 UTC` (7:00 PM PDT), running one hour after the daily Gmail classifier.

Key operational characteristics:

- **Entity Symmetrical Hierarchy**: Every family member (`Sudhanva`, `Maanasa`, `Narayana`, `Narmada`, `Rashmi`) has an identical subfolder depth (`USA/`, `India/`, `Career/`, `Education/`).
- **Media Pre-Routing**: Photos and videos are organized chronologically (`Media/YYYY/YYYY-MM/`) via EXIF and Drive metadata, bypassing the LLM completely.
- **Firecrawl Single-Page Inspection**: PDFs stream only the first page (or up to 2,000 characters) to analyze document type and reading order without downloading entire files.
- **Pydantic AI & Local Inference**: Uses `pydantic-ai` with structured output models pointing to `llama-server.llama.svc.cluster.local:8080/v1` running Google Gemma 4 (E2B).
- **LLM Folder Triage**: When non-taxonomy folders are dropped in root, Gemma analyzes the folder manifest to classify it as a code repository or an unstructured document batch.
- **Code & Project Preservation**: Folders identified as software projects, git repositories, or Jupyter notebooks are preserved intact and moved directly to `Code/<Folder_Name>` or `Colab Notebooks/<Folder_Name>`.
- **Recursive Document Dismantling**: Loose document collections are recursively traversed, files are individually filed into the symmetrical taxonomy with folder breadcrumb context, and empty folder shells are pruned bottom-up.
- **Joint Drive Shortcuts**: Joint records (Marriage Certificate, apartment leases, joint tax returns) physically reside in one place and automatically generate native Google Drive Shortcuts (`application/vnd.google-apps.shortcut`) in the partner's corresponding folder.
- **Idempotency**: Tags every processed file with `appProperties.ai_processed = true` to prevent reprocessing.

## Step 1: Verify Scheduled CronJob

To check the status and schedule of the CronJob:

```bash
kubectl -n drive-organizer get cronjob,jobs,pods
```

The schedule should reflect `0 2 * * *` with `concurrencyPolicy: Forbid`.

## Step 2: Ingesting Loose Files or Folders

You can drop items directly into the root of Google Drive (`My Drive`):

- **Loose Files**: Single PDFs, images, or documents are classified and filed directly.
- **Unorganized Document Folders**: Folders such as `Scans/`, `2024 Taxes/`, or nested folders are automatically crawled. Files inside inherit parent folder names as context for high-confidence classification, and the empty parent folders are automatically pruned after all files are evacuated.
- **Code Repositories**: Folders containing scripts, software projects, or Jupyter notebooks are detected by the local LLM and moved intact without shredding files.
- **Protected Taxonomy**: Root taxonomy directories (`Sudhanva/`, `Maanasa/`, `Code/`, `Media/`, `Review/`) are protected and will never be dismantled.

## Step 3: Trigger an Ad-Hoc Run

To trigger an immediate run outside the scheduled cron window:

```bash
kubectl -n drive-organizer create job --from=cronjob/drive-organizer drive-manual-test
```

To monitor logs in real-time:

```bash
kubectl -n drive-organizer logs -f job/drive-manual-test
```

## Step 4: Run in Dry-Run Mode

To test file classification without modifying files in Google Drive:

```bash
kubectl -n drive-organizer run drive-dry-run \
  --image=ghcr.io/nsudhanva/homelab-drive-organizer:latest \
  --restart=Never --rm -it \
  --env-from=secret/drive-credentials \
  -- python -m drive_organizer.main --dry-run --limit 10
```

## Step 5: Reviewing Quarantined Files

If a document has a low confidence score or ambiguous entity, the classifier routes it to `Review/Needs Review/` and dispatches an alert to the Telegram bot (`@ManassuHomelabBot`).
