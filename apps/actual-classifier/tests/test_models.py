"""Unit tests for models, enums, and schema constraints."""

from enum import StrEnum

import pytest
from pydantic import ValidationError

from actual_classifier.models import CategoryEnum, ClassificationResult, TagEnum, TransactionInput


@pytest.mark.parametrize("enum_cls", [CategoryEnum, TagEnum])
def test_enum_values_are_single_alpha_words(enum_cls: type[StrEnum]) -> None:
    for member in enum_cls:
        assert member.value.isalpha(), f"{enum_cls.__name__} '{member.value}' is not one word"


def test_classification_result_rejects_invalid_category() -> None:
    with pytest.raises(ValidationError):
        ClassificationResult(
            category="Food & Dining",  # type: ignore[arg-type]
            tag=None,
            clean_payee="Idly Express",
            confidence=0.95,
            reasoning="Invalid category",
        )


def test_transaction_input_dollar_conversion() -> None:
    tx = TransactionInput(
        id="tx-123",
        date="2026-09-25",
        amount_cents=-3440,
        imported_payee="Murugan Cafe",
        account_name="[Sudhanva] Amex Gold Card",
    )
    assert tx.amount_dollars == -34.40
