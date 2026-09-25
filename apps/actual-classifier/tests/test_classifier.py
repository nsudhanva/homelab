"""Unit tests for TransactionClassifier logic, guardrails, and model integration."""

from pydantic_ai.models.test import TestModel

from actual_classifier.classifier import SYSTEM_PROMPT, TransactionClassifier
from actual_classifier.config import Settings
from actual_classifier.models import CategoryEnum, TagEnum, TransactionInput
from homelab_ai import LLMClientConfig, ModelRouter
from homelab_ai.providers import CustomModelProviderBuilder


def test_classifier_success_with_test_model() -> None:
    """Test successful classification run using injected hermetic model."""
    mock_model = TestModel(
        custom_output_args={
            "category": "Food",
            "tag": None,
            "clean_payee": "Apni Mandi",
            "confidence": 0.95,
            "reasoning": "Indian grocery market",
        }
    )

    settings = Settings(confidence_threshold=0.6)
    classifier = TransactionClassifier(settings)
    # Inject hermetic model
    classifier.router = ModelRouter(
        config=LLMClientConfig(primary_provider="local", fallback_provider="none"),
        custom_primary_builder=CustomModelProviderBuilder(mock_model),
    )
    classifier.agent = classifier.router.create_agent(
        output_type=classifier.agent.output_type,
        system_prompt=SYSTEM_PROMPT,
    )

    tx = TransactionInput(
        id="t-1",
        date="2026-09-20",
        amount_cents=-4500,
        imported_payee="APNI MANDI SUNNYVALE CA",
        account_name="[Sudhanva] Amex Gold Card",
    )

    result = classifier.classify(tx)
    assert result.category == CategoryEnum.Food
    assert result.tag is None
    assert result.clean_payee == "Apni Mandi"
    assert result.confidence == 0.95


def test_classifier_low_confidence_guardrail() -> None:
    """Ensure low-confidence predictions automatically fall back to #Unknown tag."""
    mock_model = TestModel(
        custom_output_args={
            "category": "Shopping",
            "tag": None,
            "clean_payee": "Ambiguous Store",
            "confidence": 0.40,  # Below 0.6 threshold
            "reasoning": "Uncertain about merchant",
        }
    )

    settings = Settings(confidence_threshold=0.6)
    classifier = TransactionClassifier(settings)
    classifier.router = ModelRouter(
        config=LLMClientConfig(primary_provider="local", fallback_provider="none"),
        custom_primary_builder=CustomModelProviderBuilder(mock_model),
    )
    classifier.agent = classifier.router.create_agent(
        output_type=classifier.agent.output_type,
        system_prompt=SYSTEM_PROMPT,
    )

    tx = TransactionInput(
        id="t-2",
        date="2026-09-20",
        amount_cents=-1200,
        imported_payee="SOMETHING WEIRD 99",
        account_name="[Maanasa] Apple Card",
    )

    result = classifier.classify(tx)
    assert result.category == CategoryEnum.Shopping
    assert result.tag == TagEnum.Unknown
    assert "Low confidence fallback" in result.reasoning
