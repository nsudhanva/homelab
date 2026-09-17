import logging
import os

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from .sanitizer import SanitizedEmail

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
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


class EmailClassifier:
    """Classifies sanitized emails using a Pydantic AI Agent backed by a local LLM."""

    def __init__(
        self,
        base_url: str = "http://llama-server.llama.svc.cluster.local:8080/v1",
        model_name: str = "gemma-4-e2b-it",
        confidence_threshold: float = 0.80,
        quarantine_label: str = "ai-review",
        processed_label: str = "ai-processed",
        timeout_seconds: float = 120.0,
        agent: Agent[None, ClassificationResult] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.quarantine_label = quarantine_label
        self.processed_label = processed_label
        self.timeout = timeout_seconds

        if agent is not None:
            self.agent = agent
        else:
            client = AsyncOpenAI(
                base_url=self.base_url,
                api_key="not-needed",
                timeout=self.timeout,
            )
            provider = OpenAIProvider(openai_client=client)
            model = OpenAIChatModel(self.model_name, provider=provider)
            self.agent = Agent(
                model=model,
                output_type=ClassificationResult,
                system_prompt=(
                    "You are an automated email triage system.\n"
                    "Categorize each email into EXACTLY ONE active user label based on "
                    "PRIMARY INTENT.\n"
                    "CRITICAL: Do NOT fall into keyword traps. The mention of a company "
                    "or product name does NOT determine the label if the primary intent "
                    "is different.\n"
                    "If none of the candidate labels match the primary intent with high "
                    "confidence, choose 'QUARANTINE'.\n"
                    "Keep your reasoning brief (1-2 sentences)."
                ),
            )

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

    def _build_prompt(
        self,
        email: SanitizedEmail,
        curated_labels: list[str],
    ) -> str:
        labels_list_str = "\n".join(f"- {label}" for label in curated_labels)
        return (
            f"Active Allowed Labels:\n{labels_list_str}\n\n"
            f"Email to Classify:\n"
            f"Subject: {email.subject}\n"
            f"From: {email.sender}\n"
            f"Date: {email.date}\n"
            f"Snippet: {email.snippet}\n\n"
            f"Body:\n{email.body}\n\n"
            "Classification Rules & Intent Disambiguation:\n"
            "1. RECRUITMENT VS APPLICATIONS:\n"
            "   - Inbound recruiter/headhunter outreach, interview inquiries, or talent reachouts\n"
            "     -> 'Companies/Jobs'. Even if they mention past employers (e.g. Montai, Google,\n"
            "     Autodesk), do NOT classify under the past employer label.\n"
            "   - Outbound job applications, ATS confirmations (Greenhouse, Lever, Workday),\n"
            "     interview scheduling, or application outcomes/rejections (e.g. Taskrabbit)\n"
            "     -> 'Companies/Apply'.\n"
            "2. DEVELOPER & CODE PLATFORMS:\n"
            "   - GitHub notifications, PR reviews, CI/CD alerts, and automated bots like\n"
            "     Dependabot -> 'Personal/GitHub'.\n"
            "3. FAMILY MEMBER SPECIFICITY:\n"
            "   - If an email explicitly concerns, names, or schedules an appointment for a\n"
            "     specific tracked family member (e.g. Maanasa, Narayana, Rashmi, Sameera),\n"
            "     prefer the specific family label (e.g. 'Personal/Family/Maanasa') over generic\n"
            "     topical labels (like 'Personal/Health').\n"
            "4. FINANCIAL & PAYMENT METHODS:\n"
            "   - If a merchant/service receipt mentions a payment card (e.g. Amex, Chase, Visa),\n"
            "     classify by the merchant or personal category, NOT the card issuer.\n"
            "   - Dedicated financial labels ('Personal/Amex', 'Personal/Banks') are strictly for\n"
            "     emails sent directly by Amex or banks regarding statements, card alerts, or\n"
            "     fraud.\n"
            "5. HIERARCHICAL SPECIFICITY & FALLBACKS:\n"
            "   - Always prefer specific child labels (e.g. 'Personal/Amazon', 'Personal/Nike')\n"
            "     over generic parent labels ('Companies', 'Personal').\n"
            "   - Legitimate personal subscriptions or service accounts without a dedicated child\n"
            "     label (e.g. car subscriptions, utilities) should map to 'Personal'.\n"
            "   - Only use 'QUARANTINE' if the email is unsolicited spam, completely irrelevant\n"
            "     noise, or truly ambiguous.\n"
            "6. MANDATORY OUTPUT:\n"
            "   - Choose EXACTLY ONE label from the Active Allowed Labels above or 'QUARANTINE'.\n"
            "   - Provide confidence (0.0 to 1.0) and a concise 1-sentence reason focusing on "
            "sender intent."
        )

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
        """Classify an email asynchronously using the Pydantic AI Agent."""
        curated_labels = self.filter_candidate_labels(candidate_labels)
        if not curated_labels:
            logger.warning("No active curated user labels found. Falling back to quarantine.")
            return ClassificationResult(
                label=self.quarantine_label,
                confidence=0.0,
                reason="No active curated user labels available",
            )

        prompt = self._build_prompt(email, curated_labels)
        try:
            run_result = await self.agent.run(prompt)
            raw_result = run_result.output
            return self._evaluate_result(raw_result, set(curated_labels))
        except Exception as exc:
            logger.error(f"Pydantic AI classification failed for email {email.id}: {exc}")
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
        """Synchronously classify an email using the Pydantic AI Agent."""
        curated_labels = self.filter_candidate_labels(candidate_labels)
        if not curated_labels:
            logger.warning("No active curated user labels found. Falling back to quarantine.")
            return ClassificationResult(
                label=self.quarantine_label,
                confidence=0.0,
                reason="No active curated user labels available",
            )

        prompt = self._build_prompt(email, curated_labels)
        try:
            run_result = self.agent.run_sync(prompt)
            raw_result = run_result.output
            return self._evaluate_result(raw_result, set(curated_labels))
        except Exception as exc:
            logger.error(f"Pydantic AI classification failed for email {email.id}: {exc}")
            return ClassificationResult(
                label=self.quarantine_label,
                confidence=0.0,
                reason=f"Classifier error: {exc}",
            )
