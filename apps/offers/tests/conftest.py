from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from offers.catalog import Catalog, load_catalog
from offers.config import Settings
from offers.models import Account, Txn
from offers.store import Store

CATALOG_YAML = """
cards:
  - id: gold
    name: Gold Card
    issuer: Example Bank
    annual_fee: 300
    account: gold card
    fee_payee: annual fee
  - id: flex
    name: Flex Card
    issuer: Example Bank
    account: flex card
offers:
  - id: gold-coffee
    card: gold
    name: Coffee credit
    value: 7
    period: monthly
    detect:
      credit: {payee: coffee co}
      usage: {payee: coffee co}
  - id: gold-rides
    card: gold
    name: Ride cash
    value: 10
    period: monthly
    detect:
      usage: {payee: \\brides\\b, scope: any}
  - id: gold-delivery
    card: gold
    name: Delivery promo
    value: 5
    period: monthly
    valid_to: 2026-12-31
    detect:
      usage: {payee: ^deliverydash$}
      keywords: [deliverydash]
  - id: gold-travel
    card: gold
    name: Travel credit
    value: 300
    period: cardmember_year
    detect:
      credit: {payee: travel credit}
  - id: flex-activate
    card: flex
    name: Activate categories
    kind: activation
    period: quarterly
"""


@pytest.fixture
def catalog(tmp_path: Path) -> Catalog:
    path = tmp_path / "catalog.yaml"
    path.write_text(CATALOG_YAML)
    return load_catalog(path)


@pytest.fixture
def accounts() -> list[Account]:
    return [
        Account("a-gold", "Gold Card"),
        Account("a-flex", "Flex Card"),
        Account("a-other", "Other Card"),
    ]


def txn(tid: str, account: str, day: date, dollars: float, payee: str, desc: str = "") -> Txn:
    return Txn(tid, account, day, round(dollars * 100), payee, desc)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        OFFERS_DB_PATH=tmp_path / "offers.db",
        OFFERS_CATALOG_PATH=tmp_path / "catalog.yaml",
        OFFERS_PUBLIC_URL="https://offers.example.test",
        TELEGRAM_BOT_TOKEN="",
        TELEGRAM_CHAT_ID="",
    )


@pytest.fixture
def store(settings: Settings) -> Iterator[Store]:
    s = Store(settings.db_path)
    yield s
    s.close()
