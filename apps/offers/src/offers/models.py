"""Plain data types shared by the sync job, the engine, and the web app."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    closed: bool = False


@dataclass(frozen=True)
class Txn:
    """A transaction. ``amount_cents`` is negative for money out and positive for money in."""

    id: str
    account_id: str
    date: date
    amount_cents: int
    payee: str
    description: str = ""

    @property
    def text(self) -> str:
        return f"{self.payee} {self.description}".strip()

    @property
    def amount(self) -> float:
        return self.amount_cents / 100


class EvidenceKind(StrEnum):
    CREDIT = "credit"
    USAGE = "usage"


class Source(StrEnum):
    RULE = "rule"
    AI = "ai"
    MANUAL = "manual"


@dataclass(frozen=True)
class Evidence:
    offer_id: str
    account_id: str
    period_start: date
    txn_id: str
    kind: EvidenceKind
    source: Source
    amount_cents: int
    confidence: float
    reason: str


@dataclass(frozen=True)
class Candidate:
    """A transaction that the rules cannot decide for an offer."""

    offer_id: str
    account_id: str
    period_start: date
    txn: Txn
    kind: EvidenceKind
    fingerprint: str


@dataclass(frozen=True)
class AIDecision:
    match: bool
    confidence: float
    reason: str


class State(StrEnum):
    CREDITED = "credited"
    PARTIAL = "partial"
    PENDING = "pending"
    USED = "used"
    UNUSED = "unused"
    IGNORED = "ignored"
    TO_ACTIVATE = "to_activate"
    ACTIVATED = "activated"


class OverrideStatus(StrEnum):
    USED = "used"
    IGNORED = "ignored"
