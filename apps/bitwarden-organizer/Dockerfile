FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

COPY packages/homelab-ai /build/packages/homelab-ai
COPY apps/bitwarden-organizer /build/apps/bitwarden-organizer
WORKDIR /build/apps/bitwarden-organizer

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim-bookworm AS bw

ARG BW_VERSION=2026.11.0
ARG BW_SHA256=275eab92f287503b4606b06ea53ea90b6392cc9786735d0a25caad0f92109e71

ADD --checksum=sha256:${BW_SHA256} \
    https://github.com/bitwarden/clients/releases/download/cli-v${BW_VERSION}/bw-oss-linux-${BW_VERSION}.zip \
    /tmp/bw.zip
RUN python -m zipfile -e /tmp/bw.zip /opt/bw && chmod 0755 /opt/bw/bw

FROM python:3.12-slim-bookworm AS runner
WORKDIR /app

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

COPY --from=bw /opt/bw/bw /usr/local/bin/bw
COPY --from=builder --chown=appuser:appgroup /build/apps/bitwarden-organizer/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /build/apps/bitwarden-organizer/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER appuser

ENTRYPOINT ["python", "-m", "bitwarden_organizer.main"]
