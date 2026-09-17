# AI Alert Summarizer

AI-powered Alertmanager Webhook Relay for Telegram.

## Overview

The AI Alert Summarizer receives Prometheus Alertmanager webhook payloads, sends the alert context to the local in-cluster LLM (Google Gemma 4 on NVIDIA GPU), and dispatches executive, human-readable summaries directly to Telegram.

## Features

- Non-blocking async processing with FastAPI and HTTPX
- Zero external cloud dependencies (runs 100% locally on node `legion`)
- Automatic fallback: If LLM is unreachable or times out, dispatches a clean standard template so alerts are never missed
- Native HTML formatting for Telegram messages

## Endpoints

- `GET /healthz`: Liveness probe
- `GET /readyz`: Readiness probe (verifies configuration and tokens)
- `POST /webhook`: Alertmanager v4 webhook receiver
