"""Unit tests for models, enums, and schema constraints."""

import pytest
from pydantic import ValidationError

from actual_classifier.models import CategoryEnum, ClassificationResult, TagEnum, TransactionInput


def test_category_enum_contains_only_valid_single_word() -> None:
    """Ensure all categories are strictly single-word alphabetical tokens."""
    for cat in CategoryEnum:
        assert cat.value.isalpha(), f"Category '{cat.value}' contains non-alpha characters"
        assert " " not in cat.value, f"Category '{cat.value}' contains spaces"


def test_tag_enum_contains_only_valid_single_word() -> None:
    """Ensure all tags are strictly single-word alphabetical tokens."""
    for tag in TagEnum:
        assert tag.value.isalpha(), f"Tag '{tag.value}' contains non-alpha characters"
        assert " " not in tag.value, f"Tag '{tag.value}' contains spaces"


def test_classification_result_validation_success() -> None:
    """Test valid classification result parsing."""
    res = ClassificationResult(
        category=CategoryEnum.Food,
        tag=None,
        clean_payee="Idly Express",
        confidence=0.95,
        reasoning="Indian restaurant dining",
    )
    assert res.category == CategoryEnum.Food
    assert res.clean_payee == "Idly Express"
    assert res.confidence == 0.95


def test_classification_result_rejects_invalid_category() -> None:
    """Ensure Pydantic strictly rejects hallucinated/invalid category names."""
    with pytest.raises(ValidationError):
        ClassificationResult(
            category="Food & Dining",  # type: ignore[arg-type]
            tag=None,
            clean_payee="Idly Express",
            confidence=0.95,
            reasoning="Invalid category",
        )


def test_transaction_input_dollar_conversion() -> None:
    """Test integer cents to float dollars conversion property."""
    tx = TransactionInput(
        id="tx-123",
        date="2026-09-25",
        amount_cents=-3440,
        imported_payee="Murugan Cafe",
        account_name="[Sudhanva] Amex Gold Card",
    )
    assert tx.amount_dollars == -34.40
