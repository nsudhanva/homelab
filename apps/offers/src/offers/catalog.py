"""The offer catalog: cards and their offers, loaded from YAML.

Offers are data. A new card, a changed credit, or a retired offer is an edit to the
catalog file, not to the code.
"""

import hashlib
import re
from collections.abc import Iterable
from datetime import date
from enum import StrEnum
from functools import cached_property
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from offers.periods import Period

SLUG = r"^[a-z0-9][a-z0-9-]*$"


def _check_pattern(value: str) -> str:
    try:
        re.compile(value)
    except re.error as exc:
        raise ValueError(f"invalid regular expression {value!r}: {exc}") from exc
    return value


class Kind(StrEnum):
    CREDIT = "credit"
    ACTIVATION = "activation"


class Rule(BaseModel):
    """A strict match on a transaction.

    ``payee`` is a case-insensitive regular expression. It is tested against the payee name
    and against the imported bank description, one at a time.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    payee: str
    scope: Literal["card", "any"] = "card"
    min_amount: float | None = Field(default=None, ge=0)
    max_amount: float | None = Field(default=None, ge=0)

    @field_validator("payee")
    @classmethod
    def _compiles(cls, value: str) -> str:
        return _check_pattern(value)

    @cached_property
    def pattern(self) -> re.Pattern[str]:
        return re.compile(self.payee, re.IGNORECASE)

    def matches(self, fields: Iterable[str], amount: float) -> bool:
        size = abs(amount)
        if self.min_amount is not None and size < self.min_amount:
            return False
        if self.max_amount is not None and size > self.max_amount:
            return False
        return any(self.pattern.search(f.strip()) for f in fields if f)


class Detect(BaseModel):
    """How the engine finds evidence for an offer.

    - ``credit``: a positive amount on the card, posted by the issuer for the offer.
    - ``usage``: a purchase that qualifies for the offer.
    - ``keywords``: loose words. A transaction that contains one, but does not match a rule,
      goes to the AI for a decision.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    credit: Rule | None = None
    usage: Rule | None = None
    keywords: tuple[str, ...] = ()
    ai_hint: str | None = None


class Promo(BaseModel):
    """One promo of an offer that is made of separate promos, for example DoorDash promos.

    ``payee`` limits the promo to matching purchases. A promo without ``payee`` takes any
    qualifying purchase.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    value: float = Field(gt=0)
    payee: str | None = None

    @field_validator("payee")
    @classmethod
    def _compiles(cls, value: str | None) -> str | None:
        return value if value is None else _check_pattern(value)

    @property
    def value_cents(self) -> int:
        return round(self.value * 100)

    def accepts(self, fields: Iterable[str]) -> bool:
        if self.payee is None:
            return True
        return any(re.search(self.payee, f, re.IGNORECASE) for f in fields if f)


CREDIT_GRACE_DAYS = 60


class Offer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=SLUG)
    card: str = Field(pattern=SLUG)
    name: str
    value: float = Field(default=0, ge=0)
    period: Period
    kind: Kind = Kind.CREDIT
    valid_from: date | None = None
    valid_to: date | None = None
    enrollment: bool = False
    uses: int = Field(default=1, ge=1)
    group: str | None = Field(default=None, pattern=SLUG)
    how_to_use: str | None = None
    promos: tuple[Promo, ...] = ()
    detect: Detect = Detect()

    @model_validator(mode="before")
    @classmethod
    def _from_promos(cls, data: object) -> object:
        if isinstance(data, dict) and data.get("promos"):
            total = sum(float(p["value"]) for p in data["promos"])
            data = {**data, "value": data.get("value", total), "uses": len(data["promos"])}
        return data

    @model_validator(mode="after")
    def _check(self) -> "Offer":
        if self.promos and round(sum(p.value for p in self.promos), 2) != round(self.value, 2):
            raise ValueError(f"{self.id}: value must equal the sum of the promos")
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError(f"{self.id}: valid_to is before valid_from")
        if self.period is Period.ONCE and self.valid_from is None:
            raise ValueError(f"{self.id}: a once offer needs valid_from")
        if self.kind is Kind.CREDIT and self.value <= 0:
            raise ValueError(f"{self.id}: a credit offer needs a value")
        return self

    def active_on(self, day: date) -> bool:
        if self.valid_from and day < self.valid_from:
            return False
        return not (self.valid_to and day > self.valid_to)

    def accepts_credit_on(self, day: date) -> bool:
        """Issuers post some credits after the purchase, so a credit can arrive after the end."""
        if self.valid_from and day < self.valid_from:
            return False
        return not (self.valid_to and (day - self.valid_to).days > CREDIT_GRACE_DAYS)

    @property
    def value_cents(self) -> int:
        return round(self.value * 100)

    def fingerprint(self) -> str:
        """Changes when the meaning of the offer for the AI changes, so cached AI decisions
        expire. A change to a value, a date, or a rule keeps the cached decisions."""
        meaning = self.model_dump_json(
            include={"card", "name", "kind", "how_to_use", "promos"}
        ) + self.detect.model_dump_json(include={"keywords", "ai_hint"})
        return hashlib.sha256(meaning.encode()).hexdigest()[:16]


class Card(BaseModel):
    """A card product. ``account`` matches the names of the Actual accounts for this card.

    One card can match more than one account, for example two people with the same card.
    Each account gets its own copy of every offer. The card-member year starts in the month of
    the latest ``fee_payee`` transaction, or in ``anniversary_month`` when no fee is found.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=SLUG)
    name: str
    issuer: str
    annual_fee: float = Field(default=0, ge=0)
    account: str
    fee_payee: str | None = None
    anniversary_month: int | None = Field(default=None, ge=1, le=12)

    @field_validator("account", "fee_payee")
    @classmethod
    def _compiles(cls, value: str | None) -> str | None:
        return value if value is None else _check_pattern(value)

    def matches_account(self, name: str) -> bool:
        return bool(re.search(self.account, name, re.IGNORECASE))


class Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cards: tuple[Card, ...]
    offers: tuple[Offer, ...]

    @model_validator(mode="after")
    def _check(self) -> "Catalog":
        card_ids = [c.id for c in self.cards]
        offer_ids = [o.id for o in self.offers]
        for label, ids in (("card", card_ids), ("offer", offer_ids)):
            duplicates = sorted({i for i in ids if ids.count(i) > 1})
            if duplicates:
                raise ValueError(f"duplicate {label} ids: {', '.join(duplicates)}")
        unknown = sorted({o.card for o in self.offers} - set(card_ids))
        if unknown:
            raise ValueError(f"offers refer to unknown cards: {', '.join(unknown)}")
        return self

    def card(self, card_id: str) -> Card:
        return next(c for c in self.cards if c.id == card_id)

    def offer(self, offer_id: str) -> Offer | None:
        return next((o for o in self.offers if o.id == offer_id), None)

    def offers_for(self, card_id: str) -> list[Offer]:
        return [o for o in self.offers if o.card == card_id]


def load_catalog(path: Path) -> Catalog:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Catalog.model_validate(data)
