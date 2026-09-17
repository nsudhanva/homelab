import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, status

from .clients import AlertAgentClient, TelegramClient
from .config import Settings
from .models import AlertmanagerPayload
from .service import AlertSummarizerService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("alert_summarizer")

settings = Settings()
http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global http_client
    if settings.pydantic_ai_no_banner:
        os.environ["PYDANTIC_AI_NO_BANNER"] = "1"
    http_client = httpx.AsyncClient(timeout=10.0)
    logger.info("Alert Summarizer microservice started (powered by Pydantic AI)")
    yield
    if http_client and not http_client.is_closed:
        await http_client.aclose()
    logger.info("Alert Summarizer microservice stopped")


app = FastAPI(
    title="AI Alert Summarizer",
    description="Alertmanager Webhook Relay powered by Pydantic AI, local Gemma 4, and Telegram",
    version="0.2.0",
    lifespan=lifespan,
)


def get_service() -> AlertSummarizerService:
    token = settings.get_telegram_token()
    agent = AlertAgentClient(
        base_url=settings.llm_base_url,
        model_name=settings.llm_model,
        retries=settings.llm_retries,
        cluster_name=settings.cluster_name,
        environment=settings.environment,
    )
    telegram = TelegramClient(
        bot_token=token,
        chat_id=settings.telegram_chat_id,
        api_url=settings.telegram_api_url,
        timeout_seconds=settings.telegram_timeout_seconds,
        client=http_client,
    )
    return AlertSummarizerService(agent_client=agent, telegram_client=telegram)


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


@app.post("/webhook", status_code=status.HTTP_200_OK)
async def webhook(
    payload: AlertmanagerPayload, service: AlertSummarizerService = Depends(get_service)
) -> dict[str, Any]:
    count = await service.process_payload(payload)
    return {"status": "processed", "alerts_dispatched": count}
