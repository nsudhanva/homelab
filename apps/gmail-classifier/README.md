# Gmail Classifier

Daily AI-powered Gmail triage and classification runner deployed as a Kubernetes CronJob.

## Overview

- Ingests unprocessed emails for a given date from Gmail.
- Sanitizes MIME/HTML payloads into clean, compact text.
- Classifies emails against user-curated Gmail labels using a local LLM (`gemma-4-e2b-it`).
- Falls back to `ai-review` quarantine if classification confidence is below the threshold or the predicted label is uncurated.
- Tags processed emails with `ai-processed` and the predicted label.
- Sends an execution summary and highlights quarantined emails to Telegram.
