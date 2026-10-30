# Gmail Classifier

A daily AI job that sorts Gmail messages into labels. It runs as a Kubernetes CronJob.

## Overview

- Gets the unprocessed emails for a given date from Gmail.
- Cleans MIME and HTML payloads into compact text.
- Classifies each email against the Gmail labels that the user curates, with the shared `homelab-ai` model chain (Claude Haiku 5.5 first).
- Applies the `ai-review` quarantine label when the confidence is below the threshold or the model answers `QUARANTINE`. It also applies `ai-review` when a new label fails the label creation checks.
- Creates a new label when the model proposes one and `ALLOW_LABEL_CREATION=true`. The label must have a maximum of 40 characters and must not start with `CATEGORY_`.
- Runs one CronJob for each account (`gmail-classifier-personal` at 01:00, `gmail-classifier-family` at 01:15) and one weekly `--mark-all-read` CronJob for each account. `scripts/generate-account-manifests.py` generates these CronJobs from `apps/accounts.yaml`.
- Removes classified emails older than 90 days from the inbox. Emails with the `ai-review` label stay in the inbox.
- Applies `ai-processed` and the predicted label to each processed email.
- Sends a run summary to Telegram that shows the quarantined emails.
