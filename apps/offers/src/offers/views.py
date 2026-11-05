"""Read models shared by the web app and the notifications."""

import re
from dataclasses import dataclass
from datetime import date

from offers.catalog import Card, Catalog, Offer
from offers.engine import OfferStatus, statuses, unlinked_credits
from offers.models import Account, EvidenceKind, State, Txn
from offers.periods import Period
from offers.store import Store

OPEN_STATES = (State.UNUSED, State.PARTIAL, State.TO_ACTIVATE)


@dataclass(frozen=True)
class CardSummary:
    card: Card
    card_name: str
    account: Account
    annual_fee_cents: int
    current: list[OfferStatus]
    year_captured_cents: int
    year_missed_cents: int


@dataclass(frozen=True)
class Dashboard:
    today: date
    cards: list[CardSummary]
    open_cents: int
    captured_this_period_cents: int
    review_count: int
    unlinked: list[Txn]
    accounts: dict[str, Account]


def history_start(txns: list[Txn], today: date) -> date:
    """The first day with data. Each account also starts at its own first transaction."""
    return min((t.date for t in txns), default=date(today.year, 1, 1))


def all_statuses(store: Store, catalog: Catalog, today: date) -> list[OfferStatus]:
    txns = store.transactions()
    return statuses(
        catalog,
        store.accounts(),
        txns,
        store.evidence(),
        store.overrides(),
        history_start(txns, today),
        today,
    )


def build(store: Store, catalog: Catalog, today: date) -> Dashboard:
    accounts = store.accounts()
    txns = store.transactions()
    evidence = store.evidence()
    rows = statuses(
        catalog, accounts, txns, evidence, store.overrides(), history_start(txns, today), today
    )
    year_start = date(today.year, 1, 1)

    cards: list[CardSummary] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row.instance.card.id, row.instance.account.id)
        if key in seen:
            continue
        seen.add(key)
        mine = [r for r in rows if (r.instance.card.id, r.instance.account.id) == key]
        current = sorted(
            (r for r in mine if r.window.contains(today)),
            key=lambda r: (r.state not in OPEN_STATES, r.window.end, r.instance.offer.name),
        )
        year = [r for r in mine if r.window.start >= year_start]
        finished = [r for r in year if r.window.end <= today]
        cards.append(
            CardSummary(
                card=row.instance.card,
                card_name=row.instance.card.name,
                account=row.instance.account,
                annual_fee_cents=round(row.instance.card.annual_fee * 100),
                current=current,
                year_captured_cents=sum(r.captured_cents for r in year),
                year_missed_cents=sum(r.remaining_cents for r in finished),
            )
        )

    current_all = [r for c in cards for r in c.current]
    return Dashboard(
        today=today,
        cards=cards,
        open_cents=sum(r.remaining_cents for r in current_all),
        captured_this_period_cents=sum(r.captured_cents for r in current_all),
        review_count=len(store.review()),
        unlinked=unlinked_credits(catalog, accounts, txns, evidence)[:20],
        accounts={a.id: a for a in accounts},
    )


def dollars(cents: int) -> str:
    return f"${cents / 100:,.2f}"


MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


@dataclass(frozen=True)
class FeeInfo:
    """When a card's annual fee posts, and the fee year that it pays for."""

    fee_date: date | None
    anniversary_month: int | None
    source: str | None
    year_start: date | None
    year_end: date | None


def fee_info(card: Card, account: Account, txns: list[Txn], today: date) -> FeeInfo:
    fee_date = None
    if card.fee_payee:
        pattern = re.compile(card.fee_payee, re.IGNORECASE)
        fees = [
            t.date
            for t in txns
            if t.account_id == account.id and t.amount_cents < 0 and pattern.search(t.text)
        ]
        fee_date = max(fees, default=None)
    month = fee_date.month if fee_date else card.anniversary_month
    source = "fee" if fee_date else ("catalog" if card.anniversary_month else None)
    if month is None:
        return FeeInfo(fee_date, None, None, None, None)
    year = today.year if today.month >= month else today.year - 1
    start = date(year, month, 1)
    end = date(year + 1, month, 1)
    return FeeInfo(fee_date, month, source, start, end)


def cycle_text(offer: Offer, info: FeeInfo | None) -> str:
    """Explain in plain words when an offer resets."""
    period = offer.period
    if period is Period.MONTHLY:
        text = "Calendar month. Resets on the 1st of each month."
    elif period is Period.QUARTERLY:
        text = "Calendar quarter. Resets on January 1, April 1, July 1, and October 1."
    elif period is Period.SEMIANNUAL:
        text = "Calendar half-year. Resets on January 1 and July 1."
    elif period is Period.ANNUAL:
        text = "Calendar year. Resets on January 1, not on the annual fee date."
    elif period is Period.CARDMEMBER_YEAR:
        if info and info.anniversary_month:
            month = MONTHS[info.anniversary_month - 1]
            how = (
                "the month that the annual fee posted"
                if info.source == "fee"
                else "estimated from when the credit reset"
            )
            text = f"Card-member year. Resets in {month} each year ({how})."
        else:
            text = "Card-member year. Resets on the account anniversary, when the annual fee posts."
    else:
        text = "One time."
    if offer.valid_to:
        text += f" Ends {offer.valid_to:%B %-d, %Y}."
    return text


def captured_between(row: OfferStatus, txns: dict[str, Txn], start: date, end: date) -> int:
    """The part of a period's captured value that falls between ``start`` and ``end``.

    A posted credit counts on its posting date. A use without a credit counts in the period
    in which it starts.
    """
    credits = [e for e in row.evidence if e.kind is EvidenceKind.CREDIT and e.txn_id in txns]
    if credits and row.override is None:
        inside = sum(e.amount_cents for e in credits if start <= txns[e.txn_id].date < end)
        return min(inside, row.captured_cents)
    return row.captured_cents if start <= row.window.start < end else 0
