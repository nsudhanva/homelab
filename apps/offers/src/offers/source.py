"""Reads accounts and transactions from Actual Budget.

The only write to Actual is the optional bank sync, which imports new bank transactions
in the same way as the Sync button in Actual.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta

import actual.queries as q
from actual import Actual

from offers.config import Settings
from offers.models import Account, Txn

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Snapshot:
    accounts: list[Account]
    transactions: list[Txn]


def fetch(settings: Settings, today: date) -> Snapshot:
    since = today - timedelta(days=settings.lookback_days) if settings.lookback_days else None
    with Actual(
        base_url=settings.actual_server_url,
        password=settings.actual_password,
        file=settings.actual_budget_name,
    ) as actual:
        if settings.bank_sync:
            try:
                imported = actual.run_bank_sync()
                actual.commit()
                logger.info("Bank sync imported %d transactions", len(imported))
            except Exception as exc:
                logger.warning("Bank sync failed, continuing with existing data: %s", exc)

        session = actual.session
        accounts = [
            Account(a.id, a.name or a.id, bool(a.closed))
            for a in q.get_accounts(session)
            if not a.offbudget
        ]
        on_budget = {a.id for a in accounts}
        payees = {p.id: p.name or "" for p in q.get_payees(session)}
        categories = {c.id: c.name or "" for c in q.get_categories(session)}

        txns: list[Txn] = []
        for t in q.get_transactions(session, start_date=since):
            if t.acct not in on_budget or t.starting_balance_flag or t.transferred_id:
                continue
            txns.append(
                Txn(
                    id=t.id,
                    account_id=t.acct,
                    date=t.get_date(),
                    amount_cents=t.amount or 0,
                    payee=(payees.get(t.payee_id) if t.payee_id else "") or "",
                    description=t.imported_description or "",
                    category=(categories.get(t.category_id) if t.category_id else "") or "",
                )
            )
    logger.info("Read %d accounts and %d transactions", len(accounts), len(txns))
    return Snapshot(accounts, txns)
