# Gmail Classifier

A daily AI job for Gmail triage and classification that runs as a Kubernetes CronJob.

## Overview

- Gets the unprocessed emails for a given date from Gmail.
- Cleans MIME/HTML payloads into compact text.
- Classifies emails against the Gmail labels that the user curates, with the shared `homelab-ai` model chain (Claude Haiku 5.5 first).
- Applies the `ai-review` quarantine label if the classification confidence is below the threshold, the model answers `QUARANTINE`, or the predicted label is not curated and fails the label creation checks.
- Creates a new label when the model proposes one and `ALLOW_LABEL_CREATION=true` (at most 40 characters, no `CATEGORY_` prefix).
- Runs one CronJob per account (`gmail-classifier-personal` at 01:00, `gmail-classifier-family` at 01:15) and a weekly `--mark-all-read` CronJob per account. `scripts/generate-account-manifests.py` generates them from `apps/accounts.yaml`.
- Archives classified emails older than 90 days from the inbox, except `ai-review` emails.
- Tags processed emails with `ai-processed` and the predicted label.
- Sends a run summary to Telegram that shows the quarantined emails.
