import logging

from homelab_ai import AISettings, AITask, LLMOutputError
from pydantic import BaseModel, Field

from .labels import render_label_guide
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

INSTRUCTIONS = """\
You triage the Gmail inbox of Sudhanva, a machine learning engineer in the SF Bay Area \
(previously Boston, originally Bangalore), married to Maanasa.
Assign each email exactly one label based on the sender's PRIMARY INTENT.

How to decide:
1. Work out who sent the email and why: a receipt, an account alert, a person writing, \
a newsletter, a recruiter, a building notice.
2. Choose the most specific allowed label whose hint matches. A child label such as \
'Personal/Amazon' always beats its parent 'Personal'.
3. Do not fall into keyword traps. A company name in the text does not decide the label:
   - A recruiter mentioning a past employer is 'Companies/Jobs', not that employer's label.
   - A merchant receipt paid by card belongs to the merchant or 'Shopping', not the card \
issuer. Bank and card labels are only for emails sent by the bank itself.
   - Applications, interviews, and rejections for roles Sudhanva applied to are \
'Companies/Apply'; unsolicited outreach is 'Companies/Jobs'.
4. Sign-in links, one-time codes, and security notices go to the service's own label if it \
has one, otherwise to 'Personal'.
5. If an email names or schedules something for a tracked family member, prefer that \
family member's label over a topical label such as 'Personal/Health'.
6. If no allowed label fits, propose one broad Title Case category of one or two words \
(for example 'Travel' or 'Education'). Never name a label after a single sender.
7. Answer 'QUARANTINE' only for spam, phishing, or unreadable noise.

Confidence:
- 0.90 or higher when the sender or subject matches a label hint directly.
- 0.80 to 0.90 when the intent is clear but no hint names the sender.
- Below 0.80 only when two labels are genuinely plausible; the email then goes to manual review.

Give a one-sentence reason."""


class ClassificationResult(BaseModel):
    label: str = Field(description="Selected Gmail label or quarantine fallback")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reason: str = Field(description="Brief explanation of classification decision")


class EmailClassifier:
    """Classifies sanitized emails into curated Gmail labels with a homelab-ai task."""

    def __init__(
        self,
        confidence_threshold: float = 0.80,
        quarantine_label: str = "ai-review",
        processed_label: str = "ai-processed",
        allow_label_creation: bool = True,
        settings: AISettings | None = None,
        task: AITask[ClassificationResult] | None = None,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.quarantine_label = quarantine_label
        self.processed_label = processed_label
        self.allow_label_creation = allow_label_creation
        self.task = task or AITask(
            name="gmail-classifier",
            output_type=ClassificationResult,
            instructions=INSTRUCTIONS,
            settings=settings,
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

    def build_prompt(self, email: SanitizedEmail, curated_labels: list[str]) -> tuple[str, str]:
        """Return the label guide, shared by every email in a run, and the email itself."""
        labels_section = (
            render_label_guide(curated_labels)
            if curated_labels
            else "None. Propose a broad canonical label."
        )
        return f"Allowed labels:\n{labels_section}", (
            "Email:\n"
            f"From: {email.sender}\n"
            f"Subject: {email.subject}\n"
            f"Date: {email.date}\n"
            f"Snippet: {email.snippet}\n\n"
            f"Body:\n{email.body}"
        )

    def _quarantine(self, confidence: float, reason: str) -> ClassificationResult:
        return ClassificationResult(
            label=self.quarantine_label, confidence=confidence, reason=reason
        )

    def _evaluate_result(
        self,
        raw_result: ClassificationResult,
        allowed_labels: set[str],
    ) -> ClassificationResult:
        if raw_result.confidence < self.confidence_threshold:
            return self._quarantine(
                raw_result.confidence,
                f"Low confidence ({raw_result.confidence:.2f} < "
                f"{self.confidence_threshold:.2f}): {raw_result.reason}",
            )
        if raw_result.label == "QUARANTINE":
            return self._quarantine(raw_result.confidence, f"Quarantined: {raw_result.reason}")
        if raw_result.label in allowed_labels:
            return raw_result
        if self.allow_label_creation:
            cleaned = raw_result.label.strip().strip("/")
            if cleaned and len(cleaned) <= 40 and not cleaned.upper().startswith("CATEGORY_"):
                return raw_result.model_copy(update={"label": cleaned})
        return self._quarantine(
            raw_result.confidence,
            f"Unmatched label '{raw_result.label}': {raw_result.reason}",
        )

    def _prepare(
        self, email: SanitizedEmail, candidate_labels: list[str]
    ) -> tuple[tuple[str, str] | None, list[str]]:
        curated = self.filter_candidate_labels(candidate_labels)
        if not curated and not self.allow_label_creation:
            logger.warning("No active curated user labels found. Falling back to quarantine.")
            return None, curated
        return self.build_prompt(email, curated), curated

    async def classify(
        self, email: SanitizedEmail, candidate_labels: list[str]
    ) -> ClassificationResult:
        """Classify an email. LLMConnectionError propagates so batch runs can abort."""
        prompt, curated = self._prepare(email, candidate_labels)
        if prompt is None:
            return self._quarantine(0.0, "No active curated user labels available")
        try:
            labels, message = prompt
            raw = await self.task.run(message, stable_prefix=labels)
        except LLMOutputError as exc:
            return self._quarantine(0.0, f"Model output error: {exc}")
        return self._evaluate_result(raw, set(curated))

    def classify_sync(
        self, email: SanitizedEmail, candidate_labels: list[str]
    ) -> ClassificationResult:
        """Synchronous ``classify`` for worker threads."""
        prompt, curated = self._prepare(email, candidate_labels)
        if prompt is None:
            return self._quarantine(0.0, "No active curated user labels available")
        try:
            labels, message = prompt
            raw = self.task.run_sync(message, stable_prefix=labels)
        except LLMOutputError as exc:
            return self._quarantine(0.0, f"Model output error: {exc}")
        return self._evaluate_result(raw, set(curated))
