import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class TelegramClient:
    def __init__(
        self,
        bot_token: str,
        chat_id: int,
        api_url: str = "https://api.telegram.org",
        timeout_seconds: float = 5.0,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout_seconds
        self._client = client
        self._owns_client = client is None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
            self._owns_client = True
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client and not self._client.is_closed:
            await self._client.aclose()

    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        url = f"{self.api_url}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }

        try:
            client = await self.get_client()
            resp = await client.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error(f"Failed to dispatch Telegram message: {exc}")
            return False
