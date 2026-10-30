import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import Any

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status

from .clients import AlertAgentClient, TelegramClient
from .config import Settings
from .models import AlertmanagerPayload
from .service import AlertDeduplicator, AlertSummarizerService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
for noisy_logger in ("httpx", "httpx2", "httpcore"):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)
logger = logging.getLogger("alert_summarizer")

settings = Settings()
http_client: httpx.AsyncClient | None = None
deduplicator = AlertDeduplicator(window_seconds=settings.dedup_window_seconds)
agent_client = AlertAgentClient(
    cluster_name=settings.cluster_name, environment=settings.environment
)
processing_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global http_client
    http_client = httpx.AsyncClient(timeout=10.0)
    logger.info(f"Alert Summarizer started (models: {agent_client.task.describe()})")
    yield
    if http_client and not http_client.is_closed:
        await http_client.aclose()
    logger.info("Alert Summarizer microservice stopped")


app = FastAPI(
    title="AI Alert Summarizer",
    description="Alertmanager webhook relay that summarizes alerts with homelab-ai",
    version=version("alert-summarizer"),
    lifespan=lifespan,
)


def get_service() -> AlertSummarizerService:
    if http_client is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "HTTP client not started")
    token = settings.get_telegram_token()
    telegram = TelegramClient(
        client=http_client,
        bot_token=token,
        chat_id=settings.telegram_chat_id,
        api_url=settings.telegram_api_url,
        timeout_seconds=settings.telegram_timeout_seconds,
    )
    return AlertSummarizerService(
        agent_client=agent_client, telegram_client=telegram, deduplicator=deduplicator
    )


@app.get("/healthz", status_code=status.HTTP_200_OK)
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", status_code=status.HTTP_200_OK)
async def readyz() -> dict[str, str]:
    try:
        settings.get_telegram_token()
        return {"status": "ready"}
    except (ValueError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Configuration not ready: {exc}",
        ) from exc


async def process_in_background(
    service: AlertSummarizerService, payload: AlertmanagerPayload
) -> None:
    async with processing_lock:
        count = await service.process_payload(payload)
    logger.info(f"Dispatched {count} of {len(payload.alerts)} alert(s)")


@app.post("/webhook", status_code=status.HTTP_200_OK)
async def webhook(
    payload: AlertmanagerPayload,
    background_tasks: BackgroundTasks,
    service: AlertSummarizerService = Depends(get_service),
) -> dict[str, Any]:
    background_tasks.add_task(process_in_background, service, payload)
    return {"status": "accepted", "alerts_received": len(payload.alerts)}
