"""The daily job: read Actual, match offers, ask the AI about open candidates, notify."""

import logging
from datetime import date

from offers import engine
from offers.ai import Matcher
from offers.catalog import Catalog
from offers.config import Settings
from offers.models import AIDecision
from offers.notify import Sender, notify
from offers.source import Snapshot
from offers.store import Store

logger = logging.getLogger(__name__)

NO_AI = AIDecision(match=False, confidence=0.0, reason="The AI is off. Decide this one.")


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
        budget = settings.ai_max_calls
        asked = 0
        for candidate in result.pending_ai[:budget]:
            offer = catalog.offer(candidate.offer_id)
            if offer is None:
                continue
            decision = matcher.decide(candidate, offer, catalog.card(offer.card))
            if decision is None:
                break
            store.save_ai_decision(candidate, decision, matcher.model)
            asked += 1
        logger.info("Asked the AI about %d of %d candidates", asked, len(result.pending_ai))
        result = run()

    if matcher is None:
        result.review.extend((c, NO_AI) for c in result.pending_ai)
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
        f"{len(result.review)} to review, {len(result.pending_ai)} undecided, "
        f"{len(sent)} messages"
    )
