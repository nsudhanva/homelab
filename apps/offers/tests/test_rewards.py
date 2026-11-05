from datetime import date

from conftest import txn

from offers.catalog import Catalog, MerchantType
from offers.models import Account, OverrideStatus
from offers.rewards import by_month, earnings, merchant_key, uncategorized

ACCOUNTS = [Account("a-gold", "Gold Card"), Account("a-flex", "Flex Card")]


def _catalog() -> Catalog:
    return Catalog.model_validate(
        {
            "merchant_rules": {"dining": "cafe|bistro", "groceries": "grocer"},
            "cards": [
                {
                    "id": "gold",
                    "name": "Gold Card",
                    "issuer": "Example",
                    "account": "gold card",
                    "fee_payee": "annual fee",
                    "rewards": {
                        "currency": "points",
                        "point_value": 1.5,
                        "base": 1,
                        "bonuses": [
                            {
                                "name": "Dining",
                                "rate": 4,
                                "types": ["dining"],
                                "cap": {"amount": 100, "period": "year", "after_rate": 1},
                            },
                            {"name": "Shop", "rate": 5, "payee": "^shopmart$"},
                        ],
                    },
                },
                {
                    "id": "flex",
                    "name": "Flex Card",
                    "issuer": "Example",
                    "account": "flex card",
                    "rewards": {
                        "base": 1,
                        "bonuses": [
                            {
                                "name": "Quarterly 5%",
                                "rate": 5,
                                "types": ["groceries"],
                                "activation_offer": "flex-activate",
                            }
                        ],
                    },
                },
            ],
            "offers": [
                {
                    "id": "flex-activate",
                    "card": "flex",
                    "name": "Activate",
                    "kind": "activation",
                    "period": "quarterly",
                }
            ],
        }
    )


def test_bonus_cap_and_points_value() -> None:
    txns = [
        txn("d1", "a-gold", date(2026, 3, 1), -80, "Corner Cafe"),
        txn("d2", "a-gold", date(2026, 3, 2), -50, "Corner Cafe"),
        txn("s1", "a-gold", date(2026, 3, 3), -10, "Shopmart"),
        txn("x1", "a-gold", date(2026, 3, 4), -20, "Hardware"),
        txn("fee", "a-gold", date(2026, 3, 5), -300, "Annual Fee"),
        txn("pay", "a-gold", date(2026, 3, 6), 200, "Payment Thank You"),
    ]
    rows = {e.txn_id: e for e in earnings(_catalog(), ACCOUNTS, txns, {}, {}, {})}
    assert set(rows) == {"d1", "d2", "s1", "x1"}
    assert (rows["d1"].bonus, rows["d1"].points) == ("Dining", 320)
    assert rows["d2"].points == 20 * 4 + 30 * 1
    assert rows["s1"].points == 50 and rows["x1"].points == 20 and rows["x1"].bonus is None
    assert rows["d1"].value_cents == 320 * 1.5


def test_activation_gates_the_quarterly_bonus() -> None:
    cat = _catalog()
    groceries = [txn("g1", "a-flex", date(2026, 4, 10), -100, "Grocer")]
    off = earnings(cat, ACCOUNTS, groceries, {}, {}, {})[0]
    assert (off.bonus, off.value_cents, off.missed_cents) == (None, 100, 400)
    on = {("flex-activate", "a-flex", date(2026, 4, 1)): OverrideStatus.USED}
    active = earnings(cat, ACCOUNTS, groceries, {}, on, {})[0]
    assert (active.bonus, active.value_cents, active.missed_cents) == ("Quarterly 5%", 500, 0)


def test_ai_types_and_monthly_totals() -> None:
    cat = _catalog()
    txns = [
        txn("a", "a-gold", date(2026, 5, 1), -10, "SQ *Noodle House"),
        txn("b", "a-gold", date(2026, 5, 9), -10, "SQ *Noodle House"),
    ]
    assert list(uncategorized(cat, ACCOUNTS, txns, {})) == ["sq noodle house"]
    types = {merchant_key(txns[0]): MerchantType.DINING}
    assert uncategorized(cat, ACCOUNTS, txns, types) == {}
    month = by_month(earnings(cat, ACCOUNTS, txns, types, {}, {}))["a-gold"]["2026-05"]
    assert (month.spend_cents, month.points) == (2000, 80)
    assert month.by_bonus["Dining"][1] == 2000
