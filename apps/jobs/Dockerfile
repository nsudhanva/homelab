FROM oven/bun:1.4.4 AS web

WORKDIR /web
COPY apps/jobs/web/package.json apps/jobs/web/bun.lock ./
RUN bun install --frozen-lockfile
COPY apps/jobs/web ./
RUN bun run build

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

COPY packages/homelab-ai /build/packages/homelab-ai
COPY apps/jobs /build/apps/jobs
COPY --from=web /src/jobs/web_dist /build/apps/jobs/src/jobs/web_dist
WORKDIR /build/apps/jobs

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim-bookworm AS runner
WORKDIR /app

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

COPY --from=builder --chown=appuser:appgroup /build/apps/jobs/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /build/apps/jobs/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER appuser

ENTRYPOINT ["python", "-m", "jobs.cli"]
