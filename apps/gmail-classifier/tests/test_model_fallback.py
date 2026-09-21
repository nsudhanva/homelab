"""Unit tests for fallback routing in EmailClassifier."""

from typing import Any

from homelab_ai import LLMClientConfig, ModelRouter
from homelab_ai.providers import CustomModelProviderBuilder
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.models.test import TestModel

from gmail_classifier.classifier import EmailClassifier
from gmail_classifier.sanitizer import SanitizedEmail


def test_gmail_classifier_fallback_to_openrouter() -> None:
    """Verify that when the local LLM fails, EmailClassifier falls back to OpenRouter."""

    class FailingLocalModel(TestModel):
        async def request(self, *args: Any, **kwargs: Any) -> Any:
            raise ModelAPIError(model_name="gemma-4-e2b-it", message="Local LLM crashed 502")

    fallback_model = TestModel(
        custom_output_args={"label": "FINANCE", "confidence": 0.95, "reason": "Bank statement"}
    )

    router = ModelRouter(
        config=LLMClientConfig(
            primary_provider="local",
            fallback_provider="openrouter",
            openrouter_api_key="test-key",
        ),
        custom_primary_builder=CustomModelProviderBuilder(FailingLocalModel()),
        custom_fallback_builder=CustomModelProviderBuilder(fallback_model),
    )

    classifier = EmailClassifier(router=router)
    email = SanitizedEmail(
        id="msg-123",
        thread_id="th-123",
        subject="Monthly Account Statement",
        sender="service@bank.com",
        date="2026-09-20",
        snippet="Your bank statement is ready",
        body="Your monthly statement has been generated.",
    )

    result = classifier.classify_sync(email, candidate_labels=["FINANCE", "SHOPPING", "TRAVEL"])
    assert result.label == "FINANCE"
    assert result.confidence == 0.95
    assert result.reason == "Bank statement"


def test_gmail_classifier_dual_failure_quarantines() -> None:
    """Verify that when both primary and fallback fail, email is safely quarantined."""

    class AlwaysFailingModel(TestModel):
        async def request(self, *args: Any, **kwargs: Any) -> Any:
            raise ModelAPIError(model_name="test", message="Total cluster network partition")

    router = ModelRouter(
        custom_primary_builder=CustomModelProviderBuilder(AlwaysFailingModel()),
        custom_fallback_builder=CustomModelProviderBuilder(AlwaysFailingModel()),
    )

    classifier = EmailClassifier(router=router)
    email = SanitizedEmail(
        id="msg-456",
        thread_id="th-456",
        subject="Unknown email",
        sender="stranger@example.com",
        date="2026-09-20",
        snippet="hello",
        body="hello world",
    )

    # When both fail, classify_sync catches the error and falls back to quarantine
    result = classifier.classify_sync(email, candidate_labels=["FINANCE", "PERSONAL"])
    assert result.label == "ai-review"
    assert result.confidence == 0.0
