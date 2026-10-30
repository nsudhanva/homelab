"""Unit tests for TransactionClassifier logic, guardrails, and model integration."""

from typing import Any

from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.models.test import TestModel

from actual_classifier.classifier import SYSTEM_PROMPT, TransactionClassifier
from actual_classifier.config import Settings
from actual_classifier.models import (
    CategoryEnum,
    ClassificationResult,
    TagEnum,
    TransactionInput,
)
from homelab_ai import AISettings, AITask


def make_classifier(model: TestModel, threshold: float = 0.6) -> TransactionClassifier:
    task = AITask(
        name="actual-classifier",
        output_type=ClassificationResult,
        instructions=SYSTEM_PROMPT,
        settings=AISettings(_env_file=None, AI_ATTEMPTS=1),
        models=[model],
    )
    return TransactionClassifier(Settings(confidence_threshold=threshold), task=task)


def tx(payee: str, amount_cents: int = -4500) -> TransactionInput:
    return TransactionInput(
        id="t-1",
        date="2026-09-20",
        amount_cents=amount_cents,
        imported_payee=payee,
        account_name="[Sudhanva] Amex Gold Card",
    )


def output(**overrides: Any) -> TestModel:
    args = {
        "category": "Food",
        "tag": None,
        "clean_payee": "Apni Mandi",
        "confidence": 0.95,
        "reasoning": "Indian grocery market",
    }
    return TestModel(custom_output_args={**args, **overrides})


def test_classifier_success_with_test_model() -> None:
    result = make_classifier(output()).classify(tx("APNI MANDI SUNNYVALE CA"))
    assert result.category == CategoryEnum.Food
    assert result.tag is None
    assert result.clean_payee == "Apni Mandi"
    assert result.confidence == 0.95


def test_classifier_low_confidence_guardrail() -> None:
    model = output(category="Shopping", clean_payee="Ambiguous Store", confidence=0.40)
    result = make_classifier(model).classify(tx("SOMETHING WEIRD 99", -1200))
    assert result.category == CategoryEnum.Shopping
    assert result.tag == TagEnum.Unknown
    assert "Low confidence fallback" in result.reasoning


def test_classifier_falls_back_deterministically_when_llm_is_down() -> None:
    class Down(TestModel):
        async def request(self, *args: Any, **kwargs: Any) -> Any:
            raise ModelAPIError(model_name="local", message="connection refused")

    result = make_classifier(Down()).classify(tx("IRONWORKS APARTMENTS ACH DEBIT"))
    assert result.category == CategoryEnum.Rent
    assert result.tag == TagEnum.Unknown
    assert result.confidence == 0.0
