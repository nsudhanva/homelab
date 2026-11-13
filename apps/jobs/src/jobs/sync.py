"""Fetch new job threads from Gmail and run the AI extraction on them."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol

from .build import domain, personal_only
from .config import Settings
from .extract import Verdict
from .gmail import Gmail, Thread
from .store import Store, now

logger = logging.getLogger(__name__)

MAX_AI_FAILURES = 10


class Extract(Protocol):
    model: str

    def __call__(self, thread: Thread, answer: dict[str, Any] | None = None) -> Verdict: ...


def start_date(store: Store, lookback_years: int, overlap_days: int) -> date:
    """Search from the lookback start once, then from the last sync."""
    oldest = datetime.now(UTC).date() - timedelta(days=365 * lookback_years + 3)
    done = store.get_meta("searched_from")
    last = store.get_meta("last_sync")
    if last and done and date.fromisoformat(done) <= oldest:
        return datetime.fromisoformat(last).date() - timedelta(days=overlap_days)
    return oldest


def purge(store: Store, ignored: frozenset[str]) -> tuple[int, int]:
    """Delete threads with only ignored-domain people, and their contacts from verdicts."""
    if not ignored:
        return 0, 0
    gone = [t.id for t in store.threads() if personal_only(t, ignored)]
    store.delete_threads(gone)
    cleaned = 0
    for thread_id, data in store.verdicts().items():
        contacts = data.get("contacts", [])
        kept = [c for c in contacts if domain(c.get("email")) not in ignored]
        if len(kept) != len(contacts):
            store.replace_verdict_data(thread_id, {**data, "contacts": kept})
            cleaned += 1
    logger.info(f"purged {len(gone)} personal threads, cleaned {cleaned} verdicts")
    return len(gone), cleaned


def fetch(
    store: Store, gmail: Gmail, since: date, workers: int, ignored: frozenset[str] = frozenset()
) -> int:
    ids = gmail.candidate_threads(since)
    logger.info(f"{len(ids)} candidate threads since {since}")
    changed = 0
    with ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(gmail.thread, i) for i in ids]
        for n, future in enumerate(as_completed(futures), 1):
            try:
                thread = future.result()
                if ignored and personal_only(thread, ignored):
                    continue
                changed += store.save_thread(thread)
            except Exception as exc:
                logger.warning(f"could not read a thread: {exc}")
            if n % 250 == 0:
                logger.info(f"fetched {n}/{len(ids)} threads")
    logger.info(f"{changed} new or updated threads")
    return changed


def evaluate_one(
    store: Store, extract: Extract, thread_id: str, ignored: frozenset[str] = frozenset()
) -> Verdict | None:
    thread = store.thread(thread_id)
    if thread is None:
        return None
    answer = store.answer(thread_id)
    verdict = extract(thread, answer)
    verdict.contacts = [c for c in verdict.contacts if domain(c.email) not in ignored]
    if answer:
        verdict.doubt, verdict.options = None, []
    store.save_verdict(
        thread, verdict.model_dump(), extract.model, answer["created_at"] if answer else None
    )
    return verdict


def evaluate(
    store: Store,
    extract: Extract,
    workers: int,
    ignored: frozenset[str] = frozenset(),
    max_calls: int | None = None,
) -> tuple[int, int]:
    pending = store.pending(extract.model)
    pending = pending[:max_calls] if max_calls else pending
    done = failed = 0
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(evaluate_one, store, extract, t, ignored): t for t in pending}
        for future in as_completed(futures):
            try:
                future.result()
                done += 1
            except Exception as exc:
                failed += 1
                logger.warning(f"thread {futures[future]}: {exc}")
                if failed >= MAX_AI_FAILURES:
                    logger.error("too many AI failures, stopping")
                    for f in futures:
                        f.cancel()
                    break
    logger.info(f"AI: {done} threads done, {failed} failed, {len(pending)} pending at start")
    return done, failed


def sync(
    store: Store, gmail: Gmail, extract: Extract, settings: Settings, since: date | None = None
) -> None:
    started = now()
    ignored = settings.ignored_domains
    purge(store, ignored)
    since = since or start_date(store, settings.lookback_years, settings.overlap_days)
    fetch(store, gmail, since, settings.workers, ignored)
    _, failed = evaluate(store, extract, settings.workers, ignored, settings.ai_max_calls)
    if failed < MAX_AI_FAILURES:
        store.set_meta("last_sync", started)
        searched = store.get_meta("searched_from")
        if not searched or since < date.fromisoformat(searched):
            store.set_meta("searched_from", since.isoformat())
