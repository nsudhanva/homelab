import json
import logging
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field

from .sanitizer import SanitizedEmail

logger = logging.getLogger(__name__)

SYSTEM_LABELS: set[str] = {
    "INBOX",
    "SPAM",
    "TRASH",
    "UNREAD",
    "STARRED",
    "SENT",
    "DRAFT",
    "IMPORTANT",
    "CHAT",
}


class ClassificationResult(BaseModel):
    label: str = Field(description="Selected Gmail label or quarantine fallback")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reason: str = Field(description="Brief explanation of classification decision")


def extract_json_content(raw_content: str) -> dict[str, Any]:
    """Extract and parse a JSON dictionary from LLM response content."""
    clean = raw_content.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\n?", "", clean)
        clean = re.sub(r"\n?```$", "", clean).strip()

    # Search for first curly-brace block if extra text exists
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if match:
        clean = match.group(0)

    parsed = json.loads(clean)
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected JSON object, got {type(parsed)}")
    return parsed


class EmailClassifier:
    """Classifies sanitized emails using a local OpenAI-compatible LLM endpoint."""

    def __init__(
        self,
        base_url: str = "http://llama-server.llama.svc.cluster.local:8080/v1",
        model_name: str = "gemma-4-e2b-it",
        confidence_threshold: float = 0.80,
        quarantine_label: str = "ai-review",
        processed_label: str = "ai-processed",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.quarantine_label = quarantine_label
        self.processed_label = processed_label
        self.timeout = timeout_seconds

    def filter_candidate_labels(self, labels: dict[str, str] | list[str]) -> list[str]:
        """Filter out system and workflow labels to return active curated labels."""
        label_names = list(labels.keys()) if isinstance(labels, dict) else list(labels)
        candidates: list[str] = []
        for name in label_names:
            upper = name.upper()
            if upper in SYSTEM_LABELS or upper.startswith("CATEGORY_"):
                continue
            if name in {self.quarantine_label, self.processed_label}:
                continue
            candidates.append(name)
        return sorted(candidates)

    def _build_prompts(
        self,
        email: SanitizedEmail,
        curated_labels: list[str],
    ) -> tuple[str, str]:
        labels_list_str = "\n".join(f"- {label}" for label in curated_labels)
        system_prompt = (
            "You are an automated email triage system.\n"
            "Categorize the provided email into EXACTLY ONE of the following active user labels:\n"
            f"{labels_list_str}\n\n"
            "Rules:\n"
            "1. Pick the single best-fitting label from the active user labels above.\n"
            "2. If none of the allowed labels fit, or if you are uncertain, choose 'QUARANTINE'.\n"
            "3. Provide a confidence score as a float between 0.0 and 1.0.\n"
            "4. Provide a concise 1-sentence reasoning for your decision.\n"
            "5. You MUST return ONLY a JSON object with this exact schema:\n"
            '{"label": "<label or QUARANTINE>", "confidence": 0.95, "reason": "<brief rationale>"}'
        )

        user_prompt = (
            f"Subject: {email.subject}\n"
            f"From: {email.sender}\n"
            f"Date: {email.date}\n"
            f"Snippet: {email.snippet}\n\n"
            f"Body:\n{email.body}"
        )
        return system_prompt, user_prompt

    def _evaluate_result(
        self,
        raw_result: ClassificationResult,
        allowed_labels: set[str],
    ) -> ClassificationResult:
        if raw_result.confidence < self.confidence_threshold:
            return ClassificationResult(
                label=self.quarantine_label,
                confidence=raw_result.confidence,
                reason=(
                    f"Low confidence ({raw_result.confidence:.2f} < "
                    f"{self.confidence_threshold:.2f}): {raw_result.reason}"
                ),
            )

        if raw_result.label == "QUARANTINE" or raw_result.label not in allowed_labels:
            return ClassificationResult(
                label=self.quarantine_label,
                confidence=raw_result.confidence,
                reason=f"Unmatched label '{raw_result.label}': {raw_result.reason}",
            )

        return raw_result

    async def classify(
        self,
        email: SanitizedEmail,
        candidate_labels: list[str],
    ) -> ClassificationResult:
        """Classify an email asynchronously using the OpenAI-compatible completions endpoint."""
        curated_labels = self.filter_candidate_labels(candidate_labels)
        if not curated_labels:
            logger.warning("No active curated user labels found. Falling back to quarantine.")
            return ClassificationResult(
                label=self.quarantine_label,
                confidence=0.0,
                reason="No active curated user labels available",
            )

        system_prompt, user_prompt = self._build_prompts(email, curated_labels)
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        endpoint = f"{self.base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"]
            parsed_dict = extract_json_content(content)
            raw_result = ClassificationResult.model_validate(parsed_dict)
            return self._evaluate_result(raw_result, set(curated_labels))
        except Exception as exc:
            logger.error(f"Classification request failed for email {email.id}: {exc}")
            return ClassificationResult(
                label=self.quarantine_label,
                confidence=0.0,
                reason=f"Classifier error: {exc}",
            )

    def classify_sync(
        self,
        email: SanitizedEmail,
        candidate_labels: list[str],
    ) -> ClassificationResult:
        """Synchronously classify an email."""
        curated_labels = self.filter_candidate_labels(candidate_labels)
        if not curated_labels:
            logger.warning("No active curated user labels found. Falling back to quarantine.")
            return ClassificationResult(
                label=self.quarantine_label,
                confidence=0.0,
                reason="No active curated user labels available",
            )

        system_prompt, user_prompt = self._build_prompts(email, curated_labels)
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        endpoint = f"{self.base_url}/chat/completions"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"]
            parsed_dict = extract_json_content(content)
            raw_result = ClassificationResult.model_validate(parsed_dict)
            return self._evaluate_result(raw_result, set(curated_labels))
        except Exception as exc:
            logger.error(f"Classification request failed for email {email.id}: {exc}")
            return ClassificationResult(
                label=self.quarantine_label,
                confidence=0.0,
                reason=f"Classifier error: {exc}",
            )
