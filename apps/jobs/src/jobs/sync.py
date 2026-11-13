"""Fetch new job threads from Gmail and run the AI extraction on them."""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol

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


def fetch(store: Store, gmail: Gmail, since: date, workers: int) -> int:
    ids = gmail.candidate_threads(since)
    logger.info(f"{len(ids)} candidate threads since {since}")
    changed = 0
    with ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(gmail.thread, i) for i in ids]
        for n, future in enumerate(as_completed(futures), 1):
            try:
                changed += store.save_thread(future.result())
            except Exception as exc:
                logger.warning(f"could not read a thread: {exc}")
            if n % 250 == 0:
                logger.info(f"fetched {n}/{len(ids)} threads")
    logger.info(f"{changed} new or updated threads")
    return changed


def evaluate_one(store: Store, extract: Extract, thread_id: str) -> Verdict | None:
    thread = store.thread(thread_id)
    if thread is None:
        return None
    answer = store.answer(thread_id)
    verdict = extract(thread, answer)
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
    max_calls: int | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> tuple[int, int]:
    pending = store.pending(extract.model)
    pending = pending[:max_calls] if max_calls else pending
    done = failed = 0
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(evaluate_one, store, extract, t): t for t in pending}
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
            if progress and (done + failed) % 100 == 0:
                progress(done + failed, len(pending))
    logger.info(f"AI: {done} threads done, {failed} failed, {len(pending)} pending at start")
    return done, failed


def sync(
    store: Store,
    gmail: Gmail,
    extract: Extract,
    *,
    lookback_years: int,
    overlap_days: int,
    workers: int,
    since: date | None = None,
    max_calls: int | None = None,
) -> None:
    started = now()
    since = since or start_date(store, lookback_years, overlap_days)
    fetch(store, gmail, since, workers)
    _, failed = evaluate(store, extract, workers, max_calls)
    store.set_meta("last_fetch", started)
    if failed < MAX_AI_FAILURES:
        store.set_meta("last_sync", started)
        searched = store.get_meta("searched_from")
        if not searched or since < date.fromisoformat(searched):
            store.set_meta("searched_from", since.isoformat())
