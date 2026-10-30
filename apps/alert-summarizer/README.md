# AI Alert Summarizer

An Alertmanager webhook relay that sends AI summaries of alerts to Telegram.

## Overview

The AI Alert Summarizer receives Prometheus Alertmanager webhook payloads. It sends the alert context to the shared `homelab-ai` model chain: Claude Haiku 5.5, then OpenRouter, then the local Gemma 4 model. It then sends a short summary of each alert to Telegram.

## Features

- A Pydantic AI agent with typed, schema-validated output (`AlertSummary`)
- LLM retries when the output does not match the schema
- Instructions that include the cluster name and the environment
- An immediate webhook response. A FastAPI background task then processes the alerts one payload at a time, with one shared HTTPX client
- Fallback to the local Gemma 4 model in the cluster when the cloud providers are not available
- A standard template message when the full model chain is unreachable or times out, so that each alert gets to Telegram
- HTML formatting for Telegram messages

## Deployment

- The service runs as a Deployment in the `monitoring` namespace. The Service `alert-summarizer` listens on port 8000
- Alertmanager sends alerts to `http://alert-summarizer.monitoring.svc.cluster.local:8000/webhook` (refer to `infrastructure/prometheus/prometheus.yaml`)
- The service reads the model chain from the `homelab-ai` ConfigMap and the API keys from the `homelab-ai-credentials` Secret
- The service reads the Telegram bot token from `/etc/secrets/token`. This file comes from the `alertmanager-telegram` Secret (Vault `kv/telegram/bot`)
- The Dockerfile `CMD` runs `uvicorn` on `0.0.0.0:8000`

## Configuration

All settings use the `ALERT_` prefix:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ALERT_CLUSTER_NAME` | `homelab-k3s` | Cluster name in the instructions |
| `ALERT_ENVIRONMENT` | `production` | Environment name in the instructions |
| `ALERT_DEDUP_WINDOW_SECONDS` | `3000` | Ignore a repeat of the same alert fingerprint and status within this window |
| `ALERT_TELEGRAM_BOT_TOKEN` | None | Bot token. If it is not set, the service reads the token file |
| `ALERT_TELEGRAM_BOT_TOKEN_FILE` | `/etc/secrets/token` | File that holds the bot token |
| `ALERT_TELEGRAM_CHAT_ID` | `7341944813` | Target chat |
| `ALERT_TELEGRAM_TIMEOUT_SECONDS` | `5` | Telegram request timeout |
| `ALERT_TELEGRAM_API_URL` | `https://api.telegram.org` | Telegram API URL |

## Endpoints

- `GET /healthz`: Liveness probe
- `GET /readyz`: Readiness probe. It examines the configuration and the tokens
- `POST /webhook`: Alertmanager v4 webhook receiver

## Development

The project uses these tools:

- `uv` for packages and virtual environments
- `ruff` for formatting and linting
- `ty` for static type checks
- `pytest` for tests

### Commands

- Install the dependencies: `uv sync --dev`
- Run the linter: `uv run ruff check`
- Format the code: `uv run ruff format`
- Check the types: `uv run ty check`
- Run the tests: `uv run pytest`
