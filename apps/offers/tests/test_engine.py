from datetime import date

from conftest import txn

from offers import engine
from offers.catalog import Catalog, Detect, Offer, Rule
from offers.models import Account, AIDecision, EvidenceKind, OverrideStatus, Source, State
from offers.periods import Period


def _collect(catalog: Catalog, accounts: list[Account], txns, ai=None, user=None):
    return engine.collect(
        catalog,
        accounts,
        txns,
        threshold=0.85,
        ai_decisions=ai or {},
        user_decisions=user or {},
    )


def _state(catalog, accounts, txns, evidence, offer_id, day, overrides=None):
    rows = engine.statuses(catalog, accounts, txns, evidence, overrides or {}, day, day)
    return next(r for r in rows if r.instance.offer.id == offer_id)


def test_credit_and_usage_rules(catalog: Catalog, accounts: list[Account]) -> None:
    txns = [
        txn("t1", "a-gold", date(2026, 8, 3), -12.5, "Coffee Co"),
        txn("t2", "a-gold", date(2026, 8, 6), 7, "Coffee Co"),
        txn("t3", "a-other", date(2026, 8, 7), -20, "Rides"),
        txn("t4", "a-other", date(2026, 8, 8), -9, "Coffee Co"),
        txn("t5", "a-gold", date(2026, 8, 9), 50, "Payment"),
    ]
    result = _collect(catalog, accounts, txns)
    found = {(e.offer_id, e.txn_id, e.kind) for e in result.evidence}
    assert ("gold-coffee", "t1", EvidenceKind.USAGE) in found
    assert ("gold-coffee", "t2", EvidenceKind.CREDIT) in found
    assert ("gold-rides", "t3", EvidenceKind.USAGE) in found
    assert not any(e.txn_id in ("t4", "t5") for e in result.evidence)

    day = date(2026, 8, 20)
    coffee = _state(catalog, accounts, txns, result.evidence, "gold-coffee", day)
    assert coffee.state is State.CREDITED and coffee.captured_cents == 700
    rides = _state(catalog, accounts, txns, result.evidence, "gold-rides", day)
    assert rides.state is State.USED


def test_pending_and_unused(catalog: Catalog, accounts: list[Account]) -> None:
    txns = [txn("t1", "a-gold", date(2026, 9, 3), -4, "Coffee Co")]
    result = _collect(catalog, accounts, txns)
    day = date(2026, 9, 10)
    assert _state(catalog, accounts, txns, result.evidence, "gold-coffee", day).state is (
        State.PENDING
    )
    unused = _state(catalog, accounts, txns, result.evidence, "gold-delivery", day)
    assert unused.state is State.UNUSED and unused.remaining_cents == 500


def test_ai_candidates_threshold_and_user_decision(
    catalog: Catalog, accounts: list[Account]
) -> None:
    fuzzy = txn("t1", "a-gold", date(2026, 10, 2), -30, "DD *DeliveryDash Thai Place")
    result = _collect(catalog, accounts, [fuzzy])
    assert [c.offer_id for c in result.pending_ai] == ["gold-delivery"]
    fp = result.pending_ai[0].fingerprint

    sure = {("t1", "gold-delivery", fp): AIDecision(True, 0.95, "restaurant order")}
    result = _collect(catalog, accounts, [fuzzy], ai=sure)
    assert [(e.source, e.offer_id) for e in result.evidence] == [(Source.AI, "gold-delivery")]

    unsure = {("t1", "gold-delivery", fp): AIDecision(True, 0.5, "maybe")}
    result = _collect(catalog, accounts, [fuzzy], ai=unsure)
    assert not result.evidence and len(result.review) == 1

    result = _collect(catalog, accounts, [fuzzy], ai=unsure, user={("t1", "gold-delivery"): True})
    assert [e.source for e in result.evidence] == [Source.MANUAL]
    result = _collect(catalog, accounts, [fuzzy], ai=sure, user={("t1", "gold-delivery"): False})
    assert not result.evidence and not result.review


def test_ai_never_overrules_a_rule(catalog: Catalog, accounts: list[Account]) -> None:
    exact = txn("t1", "a-gold", date(2026, 10, 2), -30, "DeliveryDash")
    result = _collect(catalog, accounts, [exact])
    assert [e.source for e in result.evidence] == [Source.RULE]
    assert not result.pending_ai


def test_offer_validity(catalog: Catalog, accounts: list[Account]) -> None:
    late = txn("t1", "a-gold", date(2027, 1, 5), -30, "DeliveryDash")
    assert not _collect(catalog, accounts, [late]).evidence
    rows = engine.statuses(catalog, accounts, [], [], {}, date(2027, 1, 1), date(2027, 1, 31))
    assert "gold-delivery" not in {r.instance.offer.id for r in rows}


def test_anniversary_from_fee(catalog: Catalog, accounts: list[Account]) -> None:
    txns = [
        txn("fee", "a-gold", date(2026, 3, 4), -300, "Annual Fee"),
        txn("c1", "a-gold", date(2026, 2, 10), 100, "Travel Credit"),
    ]
    assert engine.anniversaries(catalog, accounts, txns) == {"a-gold": 3}
    result = _collect(catalog, accounts, txns)
    credit = next(e for e in result.evidence if e.offer_id == "gold-travel")
    assert credit.period_start == date(2025, 3, 1)


def test_overrides_and_activation(catalog: Catalog, accounts: list[Account]) -> None:
    day = date(2026, 11, 5)
    key = ("gold-coffee", "a-gold", date(2026, 11, 1))
    used = _state(catalog, accounts, [], [], "gold-coffee", day, {key: OverrideStatus.USED})
    assert used.state is State.USED and used.captured_cents == 700
    act = _state(catalog, accounts, [], [], "flex-activate", day)
    assert act.state is State.TO_ACTIVATE and act.remaining_cents == 0
    key = ("flex-activate", "a-flex", date(2026, 10, 1))
    done = _state(catalog, accounts, [], [], "flex-activate", day, {key: OverrideStatus.USED})
    assert done.state is State.ACTIVATED


def test_unlinked_credits(catalog: Catalog, accounts: list[Account]) -> None:
    txns = [
        txn("t1", "a-gold", date(2026, 8, 6), 7, "Coffee Co"),
        txn("t2", "a-gold", date(2026, 8, 7), 13.99, "Streaming Service"),
        txn("t3", "a-gold", date(2026, 8, 8), 100, "Payment Thank You"),
        txn("t4", "a-other", date(2026, 8, 8), 5, "Refund"),
    ]
    result = _collect(catalog, accounts, txns)
    unlinked = engine.unlinked_credits(catalog, accounts, txns, result.evidence)
    assert [t.id for t in unlinked] == ["t2"]


def test_rule_match_is_not_a_candidate_for_other_offers(
    catalog: Catalog, accounts: list[Account]
) -> None:
    credit = txn("t1", "a-gold", date(2026, 8, 6), 7, "Travel Credit")
    result = _collect(catalog, accounts, [credit])
    assert [e.offer_id for e in result.evidence] == ["gold-travel"]
    assert not result.pending_ai


def test_keywords_match_whole_words(catalog: Catalog, accounts: list[Account]) -> None:
    near_miss = txn("t1", "a-gold", date(2026, 8, 6), -9, "Mydeliverydashboard")
    assert not _collect(catalog, accounts, [near_miss]).pending_ai


def test_history_starts_with_the_account_data(catalog: Catalog, accounts: list[Account]) -> None:
    txns = [txn("t1", "a-gold", date(2026, 7, 3), -4, "Grocer")]
    rows = engine.statuses(catalog, accounts, txns, [], {}, date(2026, 1, 1), date(2026, 8, 31))
    coffee = [r.window.start.month for r in rows if r.instance.offer.id == "gold-coffee"]
    assert coffee == [7, 8]


def test_multi_use_offer_is_partial_until_all_uses(
    catalog: Catalog, accounts: list[Account]
) -> None:
    offers = tuple(
        o.model_copy(update={"uses": 2}) if o.id == "gold-rides" else o for o in catalog.offers
    )
    two_uses = Catalog(cards=catalog.cards, offers=offers)
    one = [txn("t1", "a-other", date(2026, 8, 7), -20, "Rides")]
    result = _collect(two_uses, accounts, one)
    rides = _state(two_uses, accounts, one, result.evidence, "gold-rides", date(2026, 8, 20))
    assert rides.state is State.PARTIAL
    assert (rides.captured_cents, rides.remaining_cents) == (500, 500)
    both = [*one, txn("t2", "a-other", date(2026, 8, 9), -8, "Rides")]
    result = _collect(two_uses, accounts, both)
    rides = _state(two_uses, accounts, both, result.evidence, "gold-rides", date(2026, 8, 20))
    assert rides.state is State.USED and rides.captured_cents == 1000


def test_group_gives_each_order_to_one_promo(catalog: Catalog, accounts: list[Account]) -> None:
    def promo(oid: str, value: float, uses: int, payee: str) -> Offer:
        return Offer(
            id=oid,
            card="gold",
            name=oid,
            value=value,
            uses=uses,
            period=Period.MONTHLY,
            group="dash",
            detect=Detect(usage=Rule(payee=payee)),
        )

    grouped = Catalog(
        cards=catalog.cards,
        offers=(promo("store", 20, 2, "via deliverydash"), promo("any", 15, 1, "deliverydash")),
    )
    orders = [
        txn(f"t{i}", "a-gold", date(2026, 10, i), -20, "Pharmacy via DeliveryDash")
        for i in (1, 2, 3)
    ]
    result = _collect(grouped, accounts, orders)
    owners = sorted((e.txn_id, e.offer_id) for e in result.evidence)
    assert owners == [("t1", "store"), ("t2", "store"), ("t3", "any")]


def test_anniversary_month_fallback(catalog: Catalog, accounts: list[Account]) -> None:
    cards = tuple(
        c.model_copy(update={"anniversary_month": 7, "fee_payee": None}) if c.id == "gold" else c
        for c in catalog.cards
    )
    fallback = Catalog(cards=cards, offers=catalog.offers)
    assert engine.anniversaries(fallback, accounts, []) == {"a-gold": 7}
