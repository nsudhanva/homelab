from pathlib import Path

import pytest
from pydantic import ValidationError

from offers.catalog import Catalog, load_catalog

REPO_CATALOG = Path(__file__).resolve().parents[1] / "catalog.yaml"


def test_repository_catalog_is_valid() -> None:
    catalog = load_catalog(REPO_CATALOG)
    assert catalog.cards and catalog.offers


def test_repository_catalog_has_no_account_numbers() -> None:
    text = REPO_CATALOG.read_text()
    assert "(" not in "".join(line for line in text.splitlines() if "account:" in line)


def _catalog(cards: list[dict], offers: list[dict]) -> Catalog:
    return Catalog.model_validate({"cards": cards, "offers": offers})


CARD = {"id": "c", "name": "C", "issuer": "I", "account": "c"}


def test_rejects_unknown_card() -> None:
    with pytest.raises(ValidationError, match="unknown cards"):
        _catalog([CARD], [{"id": "o", "card": "x", "name": "O", "value": 1, "period": "monthly"}])


def test_rejects_duplicate_ids() -> None:
    offer = {"id": "o", "card": "c", "name": "O", "value": 1, "period": "monthly"}
    with pytest.raises(ValidationError, match="duplicate offer"):
        _catalog([CARD], [offer, offer])


def test_rejects_bad_regex_and_missing_value() -> None:
    with pytest.raises(ValidationError):
        _catalog([{**CARD, "account": "("}], [])
    with pytest.raises(ValidationError, match="needs a value"):
        _catalog([CARD], [{"id": "o", "card": "c", "name": "O", "period": "monthly"}])


def test_fingerprint_changes_with_definition(catalog: Catalog) -> None:
    offer = catalog.offer("gold-coffee")
    assert offer is not None
    changed = offer.model_copy(update={"value": 8})
    assert offer.fingerprint() != changed.fingerprint()
