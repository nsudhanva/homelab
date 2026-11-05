"""Read models shared by the web app and the notifications."""

from dataclasses import dataclass
from datetime import date

from offers.catalog import Catalog
from offers.engine import OfferStatus, statuses, unlinked_credits
from offers.models import Account, State, Txn
from offers.store import Store

OPEN_STATES = (State.UNUSED, State.PARTIAL, State.TO_ACTIVATE)


@dataclass(frozen=True)
class CardSummary:
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
        year = [r for r in mine if r.window.end > year_start]
        finished = [r for r in year if r.window.end <= today]
        cards.append(
            CardSummary(
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
