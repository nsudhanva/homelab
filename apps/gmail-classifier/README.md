# Gmail Classifier

A daily AI job for Gmail triage and classification that runs as a Kubernetes CronJob.

## Overview

- Gets the unprocessed emails for a given date from Gmail.
- Cleans MIME/HTML payloads into compact text.
- Classifies emails against the Gmail labels that the user curates, with a local LLM (`gemma-4-e2b-it`).
- Applies the `ai-review` quarantine label if the classification confidence is below the threshold or the predicted label is not curated.
- Tags processed emails with `ai-processed` and the predicted label.
- Sends a run summary to Telegram that shows the quarantined emails.
