# AI Alert Summarizer

An Alertmanager webhook relay that sends AI alert summaries to Telegram.

## Overview

The AI Alert Summarizer receives Prometheus Alertmanager webhook payloads. It sends the alert context to the shared `homelab-ai` model chain (Claude Haiku 5.5, then OpenRouter, then the local Gemma 4 model). It then sends short, human-readable summaries directly to Telegram.

## Features

- Pydantic AI agent with strongly typed, schema-validated outputs (`AlertSummary`)
- Automatic LLM retries for self-correction if the output does not match the schema constraints
- Instructions that include the cluster name and environment
- The webhook returns at once. A background task then processes the alerts one payload at a time, with FastAPI and one shared HTTPX client
- Falls back to the local Gemma 4 model in the cluster when the cloud providers are unavailable
- Automatic fallback: if the LLM is unreachable or times out, the service sends a standard template, so no alert is lost
- Native HTML formatting for Telegram messages

## Deployment

- Runs as a Deployment (not a CronJob) in the `monitoring` namespace. The Service `alert-summarizer` listens on port 8000
- Alertmanager posts to `http://alert-summarizer.monitoring.svc.cluster.local:8000/webhook` (see `infrastructure/prometheus/prometheus.yaml`)
- Loads the model chain from the `homelab-ai` ConfigMap and the API keys from the `homelab-ai-credentials` Secret
- Reads the Telegram bot token from `/etc/secrets/token`, mounted from the `alertmanager-telegram` Secret (Vault `kv/telegram/bot`)
- The Dockerfile `CMD` runs `uvicorn` on `0.0.0.0:8000`

## Configuration

All settings use the `ALERT_` prefix:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ALERT_CLUSTER_NAME` | `homelab-k3s` | Cluster name in the instructions |
| `ALERT_ENVIRONMENT` | `production` | Environment name in the instructions |
| `ALERT_DEDUP_WINDOW_SECONDS` | `3000` | Ignore a repeat of the same alert fingerprint and status within this window |
| `ALERT_TELEGRAM_BOT_TOKEN` | None | Bot token. If unset, the service reads the token file |
| `ALERT_TELEGRAM_BOT_TOKEN_FILE` | `/etc/secrets/token` | File that holds the bot token |
| `ALERT_TELEGRAM_CHAT_ID` | `7341944813` | Target chat |
| `ALERT_TELEGRAM_TIMEOUT_SECONDS` | `5` | Telegram request timeout |
| `ALERT_TELEGRAM_API_URL` | `https://api.telegram.org` | Telegram API URL |

## Endpoints

- `GET /healthz`: Liveness probe
- `GET /readyz`: Readiness probe (examines the configuration and tokens)
- `POST /webhook`: Alertmanager v4 webhook receiver

## Development & Quality Standards

This project uses an Astral-based toolchain:

- Package and virtual environment management: `uv`
- Code formatting and linting: `ruff`
- Static type checking: `ty`
- Testing: `pytest`

### Commands

- Install dependencies: `uv sync --dev`
- Run linter: `uv run ruff check`
- Format code: `uv run ruff format`
- Check types: `uv run ty check`
- Run test suite: `uv run pytest`
