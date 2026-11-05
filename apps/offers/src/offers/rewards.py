"""Rewards earned on purchases: a base rate, and bonus rates by merchant or merchant type.

Each card in the catalog can have a ``rewards`` block. Every purchase on a card account earns
the highest bonus that applies to it, or the base rate. A bonus with a spend cap earns its
rate until the cap, then ``after_rate``. A bonus with ``activation_offer`` applies only in the
periods in which the user marked that activation offer as activated; otherwise the purchase
earns the base rate, and the difference shows as missed.
"""

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date

from offers.catalog import Bonus, Card, Catalog, MerchantType, Rewards
from offers.engine import NOT_AN_OFFER, card_accounts
from offers.models import Account, OverrideStatus, Txn
from offers.periods import Period, window_for

NOT_A_PURCHASE = re.compile(
    r"\b(annual (membership )?fee|membership fee|interest charge|late fee|cash advance)\b",
    re.IGNORECASE,
)


def merchant_key(txn: Txn) -> str:
    """A stable key for a merchant: the payee, or the bank description, without numbers."""
    text = (txn.payee or txn.description).lower()
    text = re.sub(r"[^a-z&' ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def rule_type(catalog: Catalog, txn: Txn) -> MerchantType | None:
    for kind, pattern in catalog.merchant_rules.items():
        if any(re.search(pattern, f, re.IGNORECASE) for f in (txn.payee, txn.description) if f):
            return kind
    return None


def is_purchase(card: Card, txn: Txn) -> bool:
    if txn.amount_cents >= 0 or NOT_AN_OFFER.search(txn.text) or NOT_A_PURCHASE.search(txn.text):
        return False
    return not (card.fee_payee and re.search(card.fee_payee, txn.text, re.IGNORECASE))


@dataclass(frozen=True)
class Earning:
    txn_id: str
    account_id: str
    day: date
    spend_cents: int
    bonus: str | None
    rate: float
    value_cents: float
    points: float
    missed_cents: float = 0.0


@dataclass
class MonthRewards:
    month: str
    spend_cents: int = 0
    value_cents: float = 0.0
    points: float = 0.0
    missed_cents: float = 0.0
    by_bonus: dict[str, list[float]] = field(default_factory=dict)


def _value(rewards: Rewards, spend_cents: int, rate: float) -> tuple[float, float]:
    """Return (cash value in cents, points) for a spend at a rate."""
    if rewards.currency == "cash":
        return spend_cents * rate / 100, 0.0
    points = spend_cents / 100 * rate
    return points * rewards.point_value, points


def _cap_key(bonus: Bonus, day: date, anniversary: int | None) -> tuple[str, date]:
    cap = bonus.cap
    assert cap is not None
    period = {
        "quarter": Period.QUARTERLY,
        "year": Period.ANNUAL,
        "cardmember_year": Period.CARDMEMBER_YEAR,
    }[cap.period]
    return bonus.name, window_for(period, day, anniversary).start


def _activated(
    catalog: Catalog,
    bonus: Bonus,
    account_id: str,
    day: date,
    overrides: Mapping[tuple[str, str, date], OverrideStatus],
) -> bool:
    offer = catalog.offer(bonus.activation_offer or "")
    if offer is None:
        return True
    window = window_for(offer.period, day, None, offer.valid_from)
    return overrides.get((offer.id, account_id, window.start)) is OverrideStatus.USED


def earnings(
    catalog: Catalog,
    accounts: Iterable[Account],
    txns: Iterable[Txn],
    types: Mapping[str, MerchantType],
    overrides: Mapping[tuple[str, str, date], OverrideStatus],
    anniversaries: Mapping[str, int],
) -> list[Earning]:
    ordered = sorted(txns, key=lambda t: (t.date, t.id))
    out: list[Earning] = []
    for card, account in card_accounts(catalog, accounts):
        rewards = card.rewards
        if rewards is None:
            continue
        capped: dict[tuple[str, date], int] = defaultdict(int)
        for t in ordered:
            if t.account_id != account.id or not is_purchase(card, t):
                continue
            spend = -t.amount_cents
            kind = types.get(merchant_key(t)) or rule_type(catalog, t)
            fields = (t.payee, t.description)
            base_value, base_points = _value(rewards, spend, rewards.base)
            best: tuple[float, float, Bonus, int] | None = None
            missed = 0.0
            for bonus in rewards.bonuses:
                if not bonus.active_on(t.date) or not bonus.applies(fields, kind):
                    continue
                inside = spend
                if bonus.cap:
                    used = capped[_cap_key(bonus, t.date, anniversaries.get(account.id))]
                    inside = max(0, min(spend, round(bonus.cap.amount * 100) - used))
                value, points = _value(rewards, inside, bonus.rate)
                if bonus.cap and inside < spend:
                    extra = _value(rewards, spend - inside, bonus.cap.after_rate)
                    value, points = value + extra[0], points + extra[1]
                if bonus.activation_offer and not _activated(
                    catalog, bonus, account.id, t.date, overrides
                ):
                    missed = max(missed, value - base_value)
                    continue
                if best is None or value > best[0]:
                    best = (value, points, bonus, inside)
            if best is None or best[0] <= base_value:
                out.append(
                    Earning(
                        t.id,
                        account.id,
                        t.date,
                        spend,
                        None,
                        rewards.base,
                        base_value,
                        base_points,
                        missed,
                    )
                )
                continue
            value, points, bonus, inside = best
            if bonus.cap:
                capped[_cap_key(bonus, t.date, anniversaries.get(account.id))] += inside
            out.append(
                Earning(t.id, account.id, t.date, spend, bonus.name, bonus.rate, value, points)
            )
    return out


def by_month(rows: Iterable[Earning]) -> dict[str, dict[str, MonthRewards]]:
    """Group earnings by account, then by month (YYYY-MM)."""
    out: dict[str, dict[str, MonthRewards]] = defaultdict(dict)
    for e in rows:
        key = f"{e.day.year}-{e.day.month:02d}"
        month = out[e.account_id].setdefault(key, MonthRewards(key))
        month.spend_cents += e.spend_cents
        month.value_cents += e.value_cents
        month.points += e.points
        month.missed_cents += e.missed_cents
        name = e.bonus or "Everything else"
        bucket = month.by_bonus.setdefault(name, [e.rate, 0.0, 0.0])
        bucket[1] += e.spend_cents
        bucket[2] += e.value_cents
    return out


def uncategorized(
    catalog: Catalog,
    accounts: Iterable[Account],
    txns: Iterable[Txn],
    types: Mapping[str, MerchantType],
) -> dict[str, Txn]:
    """Merchants on card accounts with rewards that have no merchant type yet."""
    cards = {a.id: c for c, a in card_accounts(catalog, accounts) if c.rewards}
    out: dict[str, Txn] = {}
    for t in txns:
        card = cards.get(t.account_id)
        if card is None or not is_purchase(card, t):
            continue
        key = merchant_key(t)
        if key and key not in types and rule_type(catalog, t) is None:
            out.setdefault(key, t)
    return out


def describe(bonus: Bonus) -> str:
    """A short plain description of where a bonus applies."""
    parts = []
    if bonus.types:
        parts.append(", ".join(t.value.replace("_", " ") for t in bonus.types))
    if bonus.note:
        parts.append(bonus.note)
    if bonus.cap:
        period = {"quarter": "quarter", "year": "year", "cardmember_year": "card year"}
        parts.append(
            f"up to ${bonus.cap.amount:,.0f} a {period[bonus.cap.period]}, "
            f"then {bonus.cap.after_rate:g}"
        )
    if bonus.activation_offer:
        parts.append("needs activation")
    if bonus.valid_from or bonus.valid_to:
        start = bonus.valid_from.strftime("%b %-d, %Y") if bonus.valid_from else "now"
        end = bonus.valid_to.strftime("%b %-d, %Y") if bonus.valid_to else "ongoing"
        parts.append(f"{start} to {end}")
    return "; ".join(parts)
