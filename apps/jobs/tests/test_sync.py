from datetime import UTC, date, datetime, timedelta

from conftest import message, thread

from jobs.store import Store
from jobs.sync import evaluate, start_date


def test_new_prompt_version_reruns_threads(tmp_path, fake):
    store = Store(tmp_path / "jobs.db")
    store.save_thread(thread("t1", message(1)))
    evaluate(store, fake, workers=1)
    assert store.pending("test#v1") == []
    assert store.pending("test#v2") == ["t1"]


def test_start_date_extends_lookback_once(tmp_path):
    store = Store(tmp_path / "jobs.db")
    today = datetime.now(UTC).date()
    assert start_date(store, 1, 3) < today - timedelta(days=365)
    store.set_meta("last_sync", f"{today}T00:00:00+00:00")
    store.set_meta("searched_from", (today - timedelta(days=400)).isoformat())
    assert start_date(store, 1, 3) == today - timedelta(days=3)
    assert start_date(store, 5, 3) < date(today.year - 4, 1, 1)
