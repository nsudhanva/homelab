import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 15.0,
        max_tokens: int = 400,
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
            "Output ONLY 3 concise, highly actionable bullet points formatted in standard HTML "
            "(use <b> for bold, <code> for kubectl or triage commands). "
            "Bullet 1: Affected component and symptom. "
            "Bullet 2: Immediate probable cause. "
            "Bullet 3: Suggested triage command or fix. "
            "Do not include intro, outro, or chain of thought."
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
            "max_tokens": 500,
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
