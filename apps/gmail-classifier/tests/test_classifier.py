from typing import Any

import pytest
from homelab_ai import AISettings, AITask, LLMConnectionError
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from gmail_classifier.classifier import INSTRUCTIONS, ClassificationResult, EmailClassifier
from gmail_classifier.sanitizer import SanitizedEmail

EMAIL = SanitizedEmail(
    id="1",
    subject="Ironworks - Daily Digest for 10/6/26",
    sender="Ironworks <noreply@realpage.com>",
    body="Here is your community status report for the past 24 hours.",
)


class Down(TestModel):
    async def request(self, *args: Any, **kwargs: Any) -> Any:
        raise ModelAPIError(model_name="local", message="connection refused")


def answer(label: str, confidence: float = 0.95, reason: str = "Matches hint") -> TestModel:
    return TestModel(
        custom_output_args={"label": label, "confidence": confidence, "reason": reason}
    )


def classifier_with(*models: Model, **kwargs: Any) -> EmailClassifier:
    task = AITask(
        name="gmail-classifier",
        output_type=ClassificationResult,
        instructions=INSTRUCTIONS,
        settings=AISettings(_env_file=None, AI_ATTEMPTS=1),
        models=list(models),
    )
    return EmailClassifier(task=task, **kwargs)


def test_filter_candidate_labels() -> None:
    labels = {
        "INBOX": "id1",
        "UNREAD": "id2",
        "SPAM": "id3",
        "CATEGORY_PROMOTIONS": "id4",
        "ai-processed": "id5",
        "ai-review": "id6",
        "Personal": "id7",
        "Work": "id8",
        "Finance": "id9",
    }
    assert classifier_with(answer("x")).filter_candidate_labels(labels) == [
        "Finance",
        "Personal",
        "Work",
    ]


def test_prompt_renders_hints_only_for_labels_the_account_has() -> None:
    labels, prompt = classifier_with(answer("x")).build_prompt(
        EMAIL, ["Personal/Doordash", "Personal/Rent"]
    )
    assert "- Personal/Rent: The current apartment building" in labels
    assert "- Personal/Doordash\n" in labels
    assert "Companies/Apply" not in labels
    assert "noreply@realpage.com" not in labels
    assert "From: Ironworks <noreply@realpage.com>" in prompt
    assert "Body:\nHere is your community status report" in prompt


def test_classify_success() -> None:
    result = classifier_with(answer("Personal/Rent")).classify(EMAIL, ["Personal/Rent"])
    assert result == ClassificationResult(
        label="Personal/Rent", confidence=0.95, reason="Matches hint"
    )


def test_classify_low_confidence_quarantines() -> None:
    result = classifier_with(answer("Personal", 0.65)).classify(EMAIL, ["Personal"])
    assert result.label == "ai-review"
    assert result.confidence == 0.65
    assert "Low confidence" in result.reason


def test_classify_unmatched_label_quarantines_when_creation_disabled() -> None:
    classifier = classifier_with(answer("Crypto"), allow_label_creation=False)
    result = classifier.classify(EMAIL, ["Personal"])
    assert result.label == "ai-review"
    assert "Unmatched label" in result.reason


def test_classify_creates_clean_new_label() -> None:
    result = classifier_with(answer("/Travel/")).classify(EMAIL, ["Personal"])
    assert result.label == "Travel"


def test_classify_explicit_quarantine() -> None:
    result = classifier_with(answer("QUARANTINE")).classify(EMAIL, ["Personal"])
    assert result.label == "ai-review"
    assert "Quarantined" in result.reason


def test_infrastructure_failure_propagates_so_batch_can_abort() -> None:
    with pytest.raises(LLMConnectionError, match="connection refused"):
        classifier_with(Down(), Down()).classify(EMAIL, ["Personal"])


def test_fallback_model_answers_when_primary_is_down() -> None:
    result = classifier_with(Down(), answer("Personal/Rent")).classify(EMAIL, ["Personal/Rent"])
    assert result.label == "Personal/Rent"


def test_invalid_model_output_quarantines() -> None:
    def garbage(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart("I think it is rent")])

    result = classifier_with(FunctionModel(garbage)).classify(EMAIL, ["Personal/Rent"])
    assert result.label == "ai-review"
    assert result.confidence == 0.0
    assert "Model output error" in result.reason


def test_no_curated_labels_skips_model_when_creation_disabled() -> None:
    model = Down()
    classifier = classifier_with(model, allow_label_creation=False)
    result = classifier.classify(EMAIL, ["INBOX", "SPAM"])
    assert result.label == "ai-review"
    assert "No active curated user labels available" in result.reason


def test_no_curated_labels_proposes_label_when_creation_enabled() -> None:
    result = classifier_with(answer("Newsletters", 0.92)).classify(EMAIL, ["INBOX"])
    assert result.label == "Newsletters"
    assert result.confidence == 0.92
