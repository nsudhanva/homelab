"""Matches transactions to offers and computes the state of each offer in each period.

The decision order is fixed:

1. Rules decide clear matches.
2. A user decision decides a candidate.
3. A cached AI decision decides a candidate when its confidence is at or above the threshold.
4. Everything else is a candidate for the AI, or goes to the review list.

The AI never overrules a rule: it only sees transactions that no rule matched.
"""

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date

from offers.catalog import Card, Catalog, Kind, Offer, Rule
from offers.models import (
    Account,
    AIDecision,
    Candidate,
    Evidence,
    EvidenceKind,
    OverrideStatus,
    Source,
    State,
    Txn,
)
from offers.periods import Window, window_for, windows_between

NOT_AN_OFFER = re.compile(
    r"\b(payment|autopay|transfer|interest|starting balance|cashback redemption|"
    r"rewards? redemption|balance adjustment)\b",
    re.IGNORECASE,
)

type DecisionKey = tuple[str, str]
type AIKey = tuple[str, str, str]


@dataclass(frozen=True)
class Instance:
    """One offer on one Actual account."""

    offer: Offer
    card: Card
    account: Account


@dataclass
class Result:
    evidence: list[Evidence] = field(default_factory=list)
    pending_ai: list[Candidate] = field(default_factory=list)
    review: list[tuple[Candidate, AIDecision]] = field(default_factory=list)


@dataclass(frozen=True)
class OfferStatus:
    instance: Instance
    window: Window
    state: State
    captured_cents: int
    evidence: tuple[Evidence, ...]
    override: OverrideStatus | None = None

    @property
    def remaining_cents(self) -> int:
        if self.state in (State.UNUSED, State.PENDING, State.PARTIAL):
            return max(self.instance.offer.value_cents - self.captured_cents, 0)
        return 0


def card_accounts(catalog: Catalog, accounts: Iterable[Account]) -> list[tuple[Card, Account]]:
    pairs = []
    for card in catalog.cards:
        pairs.extend((card, a) for a in accounts if not a.closed and card.matches_account(a.name))
    return pairs


def instances(catalog: Catalog, accounts: Iterable[Account]) -> list[Instance]:
    return [
        Instance(offer, card, account)
        for card, account in card_accounts(catalog, accounts)
        for offer in catalog.offers_for(card.id)
    ]


def anniversaries(
    catalog: Catalog, accounts: Iterable[Account], txns: Iterable[Txn]
) -> dict[str, int]:
    """Infer the card-member year from the latest annual fee on each account."""
    txns = list(txns)
    months: dict[str, int] = {}
    for card, account in card_accounts(catalog, accounts):
        if not card.fee_payee:
            continue
        pattern = re.compile(card.fee_payee, re.IGNORECASE)
        fees = [
            t
            for t in txns
            if t.account_id == account.id and t.amount_cents < 0 and pattern.search(t.text)
        ]
        if fees:
            months[account.id] = max(fees, key=lambda t: t.date).date.month
    return months


def _relevant(offer: Offer, txn: Txn, kind: EvidenceKind) -> bool:
    for word in offer.detect.keywords:
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", txn.text, re.IGNORECASE):
            return True
    return kind is EvidenceKind.CREDIT and txn.amount_cents == offer.value_cents


def collect(
    catalog: Catalog,
    accounts: Iterable[Account],
    txns: Iterable[Txn],
    *,
    threshold: float,
    ai_decisions: Mapping[AIKey, AIDecision],
    user_decisions: Mapping[DecisionKey, bool],
) -> Result:
    accounts = list(accounts)
    txns = list(txns)
    anniversary = anniversaries(catalog, accounts, txns)
    result = Result()

    pairs: list[tuple[Offer, Rule, Candidate]] = []
    for inst in instances(catalog, accounts):
        offer, account = inst.offer, inst.account
        if offer.kind is Kind.ACTIVATION:
            continue
        fingerprint = offer.fingerprint()
        for txn in txns:
            if txn.amount_cents == 0 or not offer.active_on(txn.date):
                continue
            on_card = txn.account_id == account.id
            kind = EvidenceKind.CREDIT if txn.amount_cents > 0 else EvidenceKind.USAGE
            rule = offer.detect.credit if kind is EvidenceKind.CREDIT else offer.detect.usage
            if rule is None or not (on_card or rule.scope == "any"):
                continue
            if kind is EvidenceKind.CREDIT and not on_card:
                continue
            window = window_for(offer.period, txn.date, anniversary.get(account.id))
            pairs.append(
                (offer, rule, Candidate(offer.id, account.id, window.start, txn, kind, fingerprint))
            )

    matched: set[str] = set()
    for _, rule, candidate in pairs:
        txn = candidate.txn
        if rule.matches((txn.payee, txn.description), txn.amount):
            result.evidence.append(
                make_evidence(candidate, Source.RULE, 1.0, f"rule: {rule.payee}")
            )
            matched.add(txn.id)

    for offer, _, candidate in pairs:
        txn = candidate.txn
        if txn.id in matched or NOT_AN_OFFER.search(txn.text):
            continue
        if not _relevant(offer, txn, candidate.kind):
            continue
        user = user_decisions.get((txn.id, offer.id))
        if user is not None:
            if user:
                result.evidence.append(make_evidence(candidate, Source.MANUAL, 1.0, "confirmed"))
            continue
        decision = ai_decisions.get((txn.id, offer.id, candidate.fingerprint))
        if decision is None:
            result.pending_ai.append(candidate)
        elif decision.confidence < threshold:
            result.review.append((candidate, decision))
        elif decision.match:
            reason = f"AI: {decision.reason}"
            result.evidence.append(make_evidence(candidate, Source.AI, decision.confidence, reason))
    return result


def make_evidence(candidate: Candidate, source: Source, confidence: float, reason: str) -> Evidence:
    return Evidence(
        offer_id=candidate.offer_id,
        account_id=candidate.account_id,
        period_start=candidate.period_start,
        txn_id=candidate.txn.id,
        kind=candidate.kind,
        source=source,
        amount_cents=abs(candidate.txn.amount_cents),
        confidence=confidence,
        reason=reason,
    )


def offer_status(
    inst: Instance,
    window: Window,
    evidence: Iterable[Evidence],
    override: OverrideStatus | None = None,
) -> OfferStatus:
    offer = inst.offer
    items = tuple(evidence)
    credits = sum(e.amount_cents for e in items if e.kind is EvidenceKind.CREDIT)
    used = any(e.kind is EvidenceKind.USAGE for e in items)

    def status(state: State, captured: int) -> OfferStatus:
        return OfferStatus(inst, window, state, captured, items, override)

    if offer.kind is Kind.ACTIVATION:
        if override is OverrideStatus.USED:
            return status(State.ACTIVATED, 0)
        if override is OverrideStatus.IGNORED:
            return status(State.IGNORED, 0)
        return status(State.TO_ACTIVATE, 0)
    if override is OverrideStatus.IGNORED:
        return status(State.IGNORED, min(credits, offer.value_cents))
    if override is OverrideStatus.USED:
        return status(State.USED, offer.value_cents)
    if credits >= offer.value_cents - 1:
        return status(State.CREDITED, offer.value_cents)
    if credits > 0:
        return status(State.PARTIAL, credits)
    if used:
        if offer.detect.credit is not None:
            return status(State.PENDING, 0)
        return status(State.USED, offer.value_cents)
    return status(State.UNUSED, 0)


def statuses(
    catalog: Catalog,
    accounts: Iterable[Account],
    txns: Iterable[Txn],
    evidence: Iterable[Evidence],
    overrides: Mapping[tuple[str, str, date], OverrideStatus],
    first: date,
    last: date,
) -> list[OfferStatus]:
    """Return the status of every offer instance in every window from ``first`` to ``last``."""
    accounts = list(accounts)
    txns = list(txns)
    anniversary = anniversaries(catalog, accounts, txns)
    grouped: dict[tuple[str, str, date], list[Evidence]] = defaultdict(list)
    for item in evidence:
        grouped[(item.offer_id, item.account_id, item.period_start)].append(item)

    coverage: dict[str, date] = {}
    for t in txns:
        if t.account_id not in coverage or t.date < coverage[t.account_id]:
            coverage[t.account_id] = t.date

    out: list[OfferStatus] = []
    for inst in instances(catalog, accounts):
        offer = inst.offer
        start = max(first, coverage.get(inst.account.id, first))
        if offer.valid_from:
            start = max(start, offer.valid_from)
        end = min(last, offer.valid_to) if offer.valid_to else last
        if start > end:
            continue
        for window in windows_between(offer.period, start, end, anniversary.get(inst.account.id)):
            key = (offer.id, inst.account.id, window.start)
            out.append(offer_status(inst, window, grouped.get(key, ()), overrides.get(key)))
    return out


def unlinked_credits(
    catalog: Catalog, accounts: Iterable[Account], txns: Iterable[Txn], evidence: Iterable[Evidence]
) -> list[Txn]:
    """Credits on card accounts that no offer explains. These can be offers missing from the
    catalog, or refunds."""
    card_account_ids = {a.id for _, a in card_accounts(catalog, accounts)}
    linked = {e.txn_id for e in evidence}
    return sorted(
        (
            t
            for t in txns
            if t.account_id in card_account_ids
            and t.amount_cents > 0
            and t.id not in linked
            and not NOT_AN_OFFER.search(t.text)
        ),
        key=lambda t: t.date,
        reverse=True,
    )
