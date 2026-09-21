import logging
import os
import threading
import time

from homelab_ai import LLMClientConfig, LLMConnectionError, ModelRouter
from pydantic import BaseModel, Field
from pydantic_ai import Agent

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
    """Classifies sanitized emails using a Pydantic AI Agent backed by a local LLM or fallback."""

    def __init__(
        self,
        base_url: str = "http://llama-server.llama.svc.cluster.local:8080/v1",
        model_name: str = "gemma-4-e2b-it",
        confidence_threshold: float = 0.80,
        quarantine_label: str = "ai-review",
        processed_label: str = "ai-processed",
        timeout_seconds: float = 120.0,
        allow_label_creation: bool = True,
        agent: Agent[None, ClassificationResult] | None = None,
        config: LLMClientConfig | None = None,
        router: ModelRouter | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.quarantine_label = quarantine_label
        self.processed_label = processed_label
        self.timeout = timeout_seconds
        self.allow_label_creation = allow_label_creation
        self._explicit_agent = agent
        self.config = config or LLMClientConfig(
            llm_base_url=self.base_url,
            llm_model_name=self.model_name,
            llm_timeout_seconds=self.timeout,
            app_name="homelab-gmail-classifier",
        )
        self.router = router or ModelRouter(self.config)
        self._local = threading.local()

    @property
    def agent(self) -> Agent[None, ClassificationResult]:
        """Return the classifier agent, isolated per thread to prevent event loop collisions."""
        if self._explicit_agent is not None:
            return self._explicit_agent

        if not hasattr(self._local, "agent"):
            self._local.agent = self.router.create_agent(
                output_type=ClassificationResult,
                system_prompt=(
                    "You are an automated email triage system.\n"
                    "Categorize each email into EXACTLY ONE canonical label based on "
                    "PRIMARY INTENT.\n"
                    "CRITICAL: Do NOT fall into keyword traps. The mention of a company "
                    "or product name does NOT determine the label if the primary intent "
                    "is different.\n"
                    "If candidate labels exist and match the primary intent, prefer them.\n"
                    "If none of the candidate labels match the primary intent with high "
                    "confidence, propose a concise, high-level canonical category label "
                    "(e.g. 'Newsletters', 'Travel', 'Entertainment', 'Shopping', 'Finance', "
                    "'Personal', 'Education', 'Social').\n"
                    "Only choose 'QUARANTINE' if the email is unsolicited spam, phishing, "
                    "or completely ambiguous noise.\n"
                    "Keep your reasoning brief (1-2 sentences)."
                ),
            )
        return self._local.agent

    @agent.setter
    def agent(self, value: Agent[None, ClassificationResult] | None) -> None:
        self._explicit_agent = value

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
        if curated_labels:
            labels_list_str = "\n".join(f"- {label}" for label in curated_labels)
            labels_section = f"Active Allowed Labels:\n{labels_list_str}\n\n"
        else:
            labels_section = "Active Allowed Labels: None (propose a clean canonical label)\n\n"

        return (
            f"{labels_section}"
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
            "6. LABEL SELECTION & AUTONOMOUS DISCOVERY:\n"
            "   - Prefer an existing active label if it matches sender intent.\n"
            "   - If NO active label fits, propose a concise, high-level canonical category label\n"
            "     (e.g. 'Newsletters', 'Travel', 'Entertainment', 'Shopping', 'Finance',\n"
            "     'Social').\n"
            "   - New labels must be Title Case and broad (1-2 words).\n"
            "   - Do NOT create sender-specific labels (e.g. do not name after 'Netflix').\n"
            "   - Only choose 'QUARANTINE' if the email is unsolicited spam, phishing, or noise.\n"
            "   - Provide confidence (0.0 to 1.0) and a concise 1-sentence reason."
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

        if raw_result.label == "QUARANTINE":
            return ClassificationResult(
                label=self.quarantine_label,
                confidence=raw_result.confidence,
                reason=f"Quarantined: {raw_result.reason}",
            )

        if raw_result.label in allowed_labels:
            return raw_result

        if self.allow_label_creation:
            cleaned = raw_result.label.strip().strip("/")
            if cleaned and len(cleaned) <= 40 and not cleaned.upper().startswith("CATEGORY_"):
                return ClassificationResult(
                    label=cleaned,
                    confidence=raw_result.confidence,
                    reason=raw_result.reason,
                )

        return ClassificationResult(
            label=self.quarantine_label,
            confidence=raw_result.confidence,
            reason=f"Unmatched label '{raw_result.label}': {raw_result.reason}",
        )

    async def classify(
        self,
        email: SanitizedEmail,
        candidate_labels: list[str],
    ) -> ClassificationResult:
        """Classify an email asynchronously using the Pydantic AI Agent."""
        curated_labels = self.filter_candidate_labels(candidate_labels)
        if not curated_labels and not self.allow_label_creation:
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
            err_str = str(exc).lower()
            if any(
                term in err_str
                for term in [
                    "connection",
                    "timeout",
                    "timed out",
                    "503",
                    "502",
                    "500",
                    "refused",
                    "reset by peer",
                    "server disconnected",
                    "remoteprotocolerror",
                    "event loop",
                ]
            ):
                logger.critical(
                    f"LLM infrastructure failure during inference for email {email.id}: {exc}"
                )
                raise LLMConnectionError(f"LLM endpoint unreachable or failed: {exc}") from exc

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
        if not curated_labels and not self.allow_label_creation:
            logger.warning("No active curated user labels found. Falling back to quarantine.")
            return ClassificationResult(
                label=self.quarantine_label,
                confidence=0.0,
                reason="No active curated user labels available",
            )

        prompt = self._build_prompt(email, curated_labels)
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                run_result = self.agent.run_sync(prompt)
                raw_result = run_result.output
                return self._evaluate_result(raw_result, set(curated_labels))
            except Exception as exc:
                err_str = str(exc).lower()
                is_infra_error = any(
                    term in err_str
                    for term in [
                        "connection",
                        "timeout",
                        "timed out",
                        "503",
                        "502",
                        "500",
                        "refused",
                        "reset by peer",
                        "server disconnected",
                        "remoteprotocolerror",
                        "event loop",
                    ]
                )
                if is_infra_error and attempt < max_attempts:
                    logger.warning(
                        f"Transient LLM infrastructure failure for email {email.id} "
                        f"(attempt {attempt}/{max_attempts}): {exc}. Retrying in 10s..."
                    )
                    time.sleep(10)
                    continue
                if is_infra_error:
                    logger.critical(
                        f"LLM infrastructure failure during inference for email {email.id} "
                        f"after {max_attempts} attempts: {exc}"
                    )
                    raise LLMConnectionError(f"LLM endpoint unreachable or failed: {exc}") from exc

                logger.error(
                    f"Pydantic AI classification model failure for email {email.id}: {exc}"
                )
                return ClassificationResult(
                    label=self.quarantine_label,
                    confidence=0.0,
                    reason=f"Model output error: {exc}",
                )
        return ClassificationResult(
            label=self.quarantine_label,
            confidence=0.0,
            reason="Exceeded maximum inference retry attempts",
        )
