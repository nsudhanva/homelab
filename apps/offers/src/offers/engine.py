"""Matches transactions to offers and computes the state of each offer in each period.

The decision order is fixed:

1. Rules decide clear matches.
2. A user correction decides a candidate.
3. The cached AI decision decides every other candidate, so no manual work is needed.
   A decision below the confidence threshold is also listed for an optional check.
4. A candidate without an AI decision waits for the next sync.

The AI never overrules a rule: it only sees transactions that no rule matched.
"""

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

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
from offers.periods import Period, Window, window_for, windows_between

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
    data_from: date | None = None

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
        fees = []
        if card.fee_payee:
            pattern = re.compile(card.fee_payee, re.IGNORECASE)
            fees = [
                t
                for t in txns
                if t.account_id == account.id and t.amount_cents < 0 and pattern.search(t.text)
            ]
        if fees:
            months[account.id] = max(fees, key=lambda t: t.date).date.month
        elif card.anniversary_month:
            months[account.id] = card.anniversary_month
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
            if txn.amount_cents == 0:
                continue
            kind = EvidenceKind.CREDIT if txn.amount_cents > 0 else EvidenceKind.USAGE
            active = offer.accepts_credit_on if kind is EvidenceKind.CREDIT else offer.active_on
            if not active(txn.date):
                continue
            on_card = txn.account_id == account.id
            rule = offer.detect.credit if kind is EvidenceKind.CREDIT else offer.detect.usage
            if rule is None or not (on_card or rule.scope == "any"):
                continue
            if kind is EvidenceKind.CREDIT and not on_card:
                continue
            window = window_for(
                offer.period, txn.date, anniversary.get(account.id), offer.valid_from
            )
            pairs.append(
                (offer, rule, Candidate(offer.id, account.id, window.start, txn, kind, fingerprint))
            )

    matched: set[str] = set()
    credited: set[str] = set()
    for _, rule, candidate in pairs:
        txn = candidate.txn
        if not rule.matches((txn.payee, txn.description), txn.amount):
            continue
        if candidate.kind is EvidenceKind.CREDIT:
            if txn.id in credited:
                continue
            credited.add(txn.id)
        result.evidence.append(make_evidence(candidate, Source.RULE, 1.0, f"rule: {rule.payee}"))
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
        else:
            if decision.match:
                reason = f"AI: {decision.reason}"
                result.evidence.append(
                    make_evidence(candidate, Source.AI, decision.confidence, reason)
                )
            if decision.confidence < threshold:
                result.review.append((candidate, decision))
    by_id = {t.id: t for t in txns}
    result.evidence = _allocate(catalog, result.evidence)
    result.evidence = _pair_credits(catalog, result.evidence, by_id)
    result.evidence = _assign_promos(catalog, result.evidence, by_id)
    return result


PAIR_DAYS = 45


def _pair_credits(
    catalog: Catalog, evidence: list[Evidence], txns: Mapping[str, Txn]
) -> list[Evidence]:
    """Move each issuer credit to the period of the purchase that it pays back.

    An issuer can post a credit some days after the purchase, in the next period. The credit
    goes to the latest earlier purchase for the same offer, within 45 days, that has no
    credit yet.
    """
    offers = {o.id: o for o in catalog.offers}
    purchases: dict[tuple[str, str], list[Evidence]] = defaultdict(list)
    for e in evidence:
        if e.kind is EvidenceKind.USAGE and e.txn_id in txns:
            purchases[(e.offer_id, e.account_id)].append(e)
    paired: set[str] = set()
    out: list[Evidence] = []
    credits = sorted(
        (e for e in evidence if e.kind is EvidenceKind.CREDIT and e.txn_id in txns),
        key=lambda e: txns[e.txn_id].date,
    )
    moved: dict[int, Evidence] = {}
    for credit in credits:
        offer = offers.get(credit.offer_id)
        if offer is None or offer.detect.usage is None:
            continue
        day = txns[credit.txn_id].date
        options = [
            p
            for p in purchases[(credit.offer_id, credit.account_id)]
            if p.txn_id not in paired and 0 <= (day - txns[p.txn_id].date).days <= PAIR_DAYS
        ]
        if not options:
            continue
        purchase = max(options, key=lambda p: txns[p.txn_id].date)
        paired.add(purchase.txn_id)
        if purchase.period_start != credit.period_start:
            moved[id(credit)] = replace(credit, period_start=purchase.period_start)
    for e in evidence:
        out.append(moved.get(id(e), e))
    return out


def _assign_promos(
    catalog: Catalog, evidence: list[Evidence], txns: Mapping[str, Txn]
) -> list[Evidence]:
    """Give each purchase to one promo of an offer that is made of promos.

    Each purchase, in date order, takes the first free promo whose ``payee`` matches it. A
    promo without ``payee`` takes a purchase only when no specific promo matches.
    """
    offers = {o.id: o for o in catalog.offers if o.promos}
    if not offers:
        return evidence
    groups: dict[tuple[str, str, date], list[Evidence]] = defaultdict(list)
    for e in evidence:
        if e.kind is EvidenceKind.USAGE and e.offer_id in offers:
            groups[(e.offer_id, e.account_id, e.period_start)].append(e)
    assigned: dict[int, Evidence] = {}
    for (offer_id, _, _), items in groups.items():
        promos = list(offers[offer_id].promos)
        free = [True] * len(promos)
        for e in sorted(
            items, key=lambda e: (txns[e.txn_id].date if e.txn_id in txns else date.min, e.txn_id)
        ):
            txn = txns.get(e.txn_id)
            fields = (txn.payee, txn.description) if txn else ()
            choice = next(
                (i for i, p in enumerate(promos) if free[i] and p.payee and p.accepts(fields)),
                None,
            )
            if choice is None:
                choice = next(
                    (i for i, p in enumerate(promos) if free[i] and p.payee is None), None
                )
            if choice is not None:
                free[choice] = False
                assigned[id(e)] = replace(e, promo_cents=promos[choice].value_cents)
    return [assigned.get(id(e), e) for e in evidence]


def _allocate(catalog: Catalog, evidence: list[Evidence]) -> list[Evidence]:
    """Give each purchase to one offer in a group.

    Offers in the same ``group`` are separate promos that one order cannot share, for example
    the DoorDash promos of a card. A purchase goes to the first offer in catalog order that
    matches it and has a use left in its period.
    """
    order = {o.id: i for i, o in enumerate(catalog.offers)}
    group_of = {o.id: o.group for o in catalog.offers if o.group}
    uses_of = {o.id: o.uses for o in catalog.offers}
    shared = [e for e in evidence if e.kind is EvidenceKind.USAGE and e.offer_id in group_of]
    if not shared:
        return evidence
    by_txn: dict[tuple[str, str, str], list[Evidence]] = defaultdict(list)
    for e in shared:
        by_txn[(e.account_id, group_of[e.offer_id], e.txn_id)].append(e)
    order_key = {e.txn_id: (e.period_start, e.txn_id) for e in shared}
    used: dict[tuple[str, str, date], int] = defaultdict(int)
    keep: set[int] = set()
    for key in sorted(by_txn, key=lambda k: order_key[k[2]]):
        options = sorted(by_txn[key], key=lambda e: order[e.offer_id])
        chosen = next(
            (
                e
                for e in options
                if used[(e.offer_id, e.account_id, e.period_start)] < uses_of[e.offer_id]
            ),
            options[0],
        )
        used[(chosen.offer_id, chosen.account_id, chosen.period_start)] += 1
        keep.add(id(chosen))
    return [
        e
        for e in evidence
        if e.offer_id not in group_of or e.kind is EvidenceKind.CREDIT or id(e) in keep
    ]


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
    uses = len({e.txn_id for e in items if e.kind is EvidenceKind.USAGE})
    if offer.promos:
        uses = sum(1 for e in items if e.kind is EvidenceKind.USAGE and e.promo_cents)

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
        return status(State.CREDITED, min(credits, offer.value_cents))
    if credits > 0:
        return status(State.PARTIAL, credits)
    if uses and offer.detect.credit is not None:
        return status(State.PENDING, 0)
    if uses >= offer.uses:
        return status(State.USED, offer.value_cents)
    if uses and offer.promos:
        return status(State.PARTIAL, sum(e.promo_cents for e in items))
    if uses:
        return status(State.PARTIAL, offer.value_cents * uses // offer.uses)
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
        if offer.period is Period.ONCE:
            first_window = window_for(offer.period, start, None, offer.valid_from)
            windows = [first_window]
        else:
            windows = windows_between(offer.period, start, end, anniversary.get(inst.account.id))
        for window in windows:
            key = (offer.id, inst.account.id, window.start)
            if offer.valid_to and window.end > offer.valid_to + timedelta(days=1):
                window = Window(window.start, offer.valid_to + timedelta(days=1))
            row = offer_status(inst, window, grouped.get(key, ()), overrides.get(key))
            seen = coverage.get(inst.account.id)
            if seen and (seen - max(window.start, offer.valid_from or window.start)).days > 7:
                row = replace(row, data_from=seen)
            out.append(row)
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
