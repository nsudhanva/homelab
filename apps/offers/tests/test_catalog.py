from pathlib import Path

import pytest
from pydantic import ValidationError

from offers.catalog import Catalog, load_catalog

REPO_CATALOG = Path(__file__).resolve().parents[1] / "catalog.yaml"


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


def test_fingerprint_follows_the_meaning_of_the_offer(catalog: Catalog) -> None:
    offer = catalog.offer("gold-coffee")
    assert offer is not None
    assert offer.fingerprint() == offer.model_copy(update={"value": 8}).fingerprint()
    changed = offer.model_copy(update={"how_to_use": "Only at the airport store."})
    assert offer.fingerprint() != changed.fingerprint()


def test_promos_set_value_and_uses() -> None:
    catalog = _catalog(
        [CARD],
        [
            {
                "id": "o",
                "card": "c",
                "name": "O",
                "period": "monthly",
                "promos": [{"name": "a", "value": 5}, {"name": "b", "value": 10, "payee": "x"}],
            }
        ],
    )
    offer = catalog.offers[0]
    assert (offer.value, offer.uses) == (15, 2)
    with pytest.raises(ValidationError, match="sum of the promos"):
        _catalog(
            [CARD],
            [
                {
                    "id": "o",
                    "card": "c",
                    "name": "O",
                    "value": 9,
                    "period": "monthly",
                    "promos": [{"name": "a", "value": 5}],
                }
            ],
        )


def test_uber_cash_rule_skips_the_uber_one_fee() -> None:
    catalog = load_catalog(REPO_CATALOG)
    assert catalog.cards and catalog.offers
    offer = catalog.offer("amex-gold-uber-cash")
    assert offer is not None and offer.detect.usage is not None
    rule = offer.detect.usage
    assert rule.matches(("Uber", "UBER *TRIP"), -20)
    assert rule.matches(("Uber Eats", ""), -30)
    assert not rule.matches(("UBER *ONE MEMBERSHIP", ""), -9.99)
    assert not rule.matches(("Uber One", ""), -9.99)


def test_once_offer_needs_a_start() -> None:
    with pytest.raises(ValidationError, match="needs valid_from"):
        _catalog(
            [CARD], [{"id": "o", "card": "c", "name": "O", "kind": "activation", "period": "once"}]
        )
