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


@pytest.mark.parametrize(
    ("label", "confidence", "allow_creation", "candidates", "expected_label", "reason_part"),
    [
        pytest.param(
            "Personal/Rent",
            0.95,
            True,
            ["Personal/Rent"],
            "Personal/Rent",
            "Matches hint",
            id="allowed-label",
        ),
        pytest.param(
            "Personal",
            0.65,
            True,
            ["Personal"],
            "ai-review",
            "Low confidence",
            id="low-confidence",
        ),
        pytest.param(
            "Crypto",
            0.95,
            False,
            ["Personal"],
            "ai-review",
            "Unmatched label",
            id="unmatched-label-creation-disabled",
        ),
        pytest.param(
            "/Travel/",
            0.95,
            True,
            ["Personal"],
            "Travel",
            "Matches hint",
            id="creates-clean-new-label",
        ),
        pytest.param(
            "QUARANTINE",
            0.95,
            True,
            ["Personal"],
            "ai-review",
            "Quarantined",
            id="explicit-quarantine",
        ),
        pytest.param(
            "Newsletters",
            0.92,
            True,
            ["INBOX"],
            "Newsletters",
            "Matches hint",
            id="no-curated-labels-proposes-label",
        ),
    ],
)
def test_classify_decision(
    label: str,
    confidence: float,
    allow_creation: bool,
    candidates: list[str],
    expected_label: str,
    reason_part: str,
) -> None:
    classifier = classifier_with(answer(label, confidence), allow_label_creation=allow_creation)
    result = classifier.classify(EMAIL, candidates)
    assert result.label == expected_label
    assert result.confidence == confidence
    assert reason_part in result.reason


def test_infrastructure_failure_propagates_so_batch_can_abort() -> None:
    with pytest.raises(LLMConnectionError, match="connection refused"):
        classifier_with(Down(), Down()).classify(EMAIL, ["Personal"])


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
