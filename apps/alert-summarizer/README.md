# AI Alert Summarizer

An Alertmanager webhook relay that sends AI alert summaries to Telegram.

## Overview

The AI Alert Summarizer receives Prometheus Alertmanager webhook payloads. It sends the alert context to the shared `homelab-ai` model chain (Claude Haiku 5.5, then OpenRouter, then the local Gemma 4 model). It then sends short, human-readable summaries directly to Telegram.

## Features

- Pydantic AI agent with strongly typed, schema-validated outputs (`AlertSummary`)
- Automatic LLM retries for self-correction if the output does not match the schema constraints
- Instructions that include the cluster name and environment
- Non-blocking async processing with FastAPI and HTTPX
- Falls back to the local Gemma 4 model in the cluster when the cloud providers are unavailable
- Automatic fallback: if the LLM is unreachable or times out, the service sends a standard template, so no alert is lost
- Native HTML formatting for Telegram messages

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
