FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

COPY packages/homelab-ai /build/packages/homelab-ai
COPY apps/alert-summarizer /build/apps/alert-summarizer
WORKDIR /build/apps/alert-summarizer

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim-bookworm AS runner
WORKDIR /app

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

COPY --from=builder --chown=appuser:appgroup /build/apps/alert-summarizer/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /build/apps/alert-summarizer/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "alert_summarizer.main:app", "--host", "0.0.0.0", "--port", "8000"]
