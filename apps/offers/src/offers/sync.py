"""The daily job: read Actual, match offers, ask the AI about open candidates, notify."""

import logging
from datetime import date

from offers import engine
from offers.ai import Matcher
from offers.catalog import Catalog
from offers.config import Settings
from offers.notify import Sender, notify
from offers.source import Snapshot
from offers.store import Store

logger = logging.getLogger(__name__)

MAX_AI_FAILURES = 3


def evaluate(
    store: Store,
    catalog: Catalog,
    settings: Settings,
    matcher: Matcher | None,
) -> engine.Result:
    """Match the stored snapshot, decide new candidates with the AI, and store the result."""
    accounts, txns = store.accounts(), store.transactions()

    def run() -> engine.Result:
        return engine.collect(
            catalog,
            accounts,
            txns,
            threshold=settings.ai_confidence_threshold,
            ai_decisions=store.ai_decisions(),
            user_decisions=store.user_decisions(),
        )

    result = run()
    if matcher and result.pending_ai:
        asked = failures = 0
        newest_first = sorted(result.pending_ai, key=lambda c: c.txn.date, reverse=True)
        for candidate in newest_first[: settings.ai_max_calls]:
            offer = catalog.offer(candidate.offer_id)
            if offer is None:
                continue
            decision = matcher.decide(candidate, offer, catalog.card(offer.card))
            if decision is None:
                failures += 1
                if failures >= MAX_AI_FAILURES:
                    logger.warning("The AI failed %d times in a row; the rest waits", failures)
                    break
                continue
            failures = 0
            store.save_ai_decision(candidate, decision, matcher.model)
            asked += 1
        logger.info("Asked the AI about %d of %d candidates", asked, len(result.pending_ai))
        result = run()

    store.replace_evidence(result.evidence)
    store.replace_review(result.review)
    return result


def sync(
    store: Store,
    catalog: Catalog,
    settings: Settings,
    snapshot: Snapshot,
    today: date,
    matcher: Matcher | None,
    sender: Sender | None,
) -> str:
    store.replace_snapshot(snapshot.accounts, snapshot.transactions)
    result = evaluate(store, catalog, settings, matcher)
    sent = notify(store, catalog, settings, today, sender) if sender else []
    return (
        f"{len(snapshot.transactions)} transactions, {len(result.evidence)} evidence, "
        f"{len(result.review)} low-confidence AI, {len(result.pending_ai)} undecided, "
        f"{len(sent)} messages"
    )
