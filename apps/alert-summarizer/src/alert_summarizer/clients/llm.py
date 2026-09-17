import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 4.0,
        max_tokens: int = 160,
        temperature: float = 0.2,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout_seconds
        self.max_tokens = max_tokens
        self.temperature = temperature
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

    async def summarize_alert(self, alert_context: str, is_resolved: bool) -> Optional[str]:
        system_prompt = (
            "You are an expert SRE on-call bot for a Kubernetes homelab cluster. "
            "Your task is to summarize the following infrastructure alert for a Telegram notification. "
            "Requirements:\n"
            "1. Output exactly 3 concise bullet points formatted in standard HTML (use <b> for bold, <code> for commands).\n"
            "2. First bullet: Affected component & core symptom.\n"
            "3. Second bullet: Probable root cause.\n"
            "4. Third bullet: Suggested triage command (e.g. <code>kubectl logs ...</code> or <code>kubectl describe ...</code>).\n"
            "5. If the alert is RESOLVED, simply state that the service recovered and duration/status.\n"
            "6. Keep the entire response under 60 words. No intro or outro text, only the bullet points."
        )

        user_content = (
            f"Alert State: {'RESOLVED' if is_resolved else 'FIRING'}\n\n"
            f"Alert Details:\n{alert_context}"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        try:
            client = await self.get_client()
            url = f"{self.base_url}/chat/completions"
            resp = await client.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content if content else None
        except Exception as exc:
            logger.warning(f"LLM summarization failed: {exc}")
            return None
