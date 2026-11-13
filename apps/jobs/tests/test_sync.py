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


def test_purge_deletes_gmail_threads_and_contacts(tmp_path, fake):
    from conftest import verdict

    from jobs.sync import purge

    store = Store(tmp_path / "jobs.db")
    store.save_thread(thread("t1", message(1, sender="friend@gmail.com")))
    store.save_thread(thread("t2", message(2)))
    evaluate(store, fake, workers=1)
    data = verdict(
        contacts=[
            {"name": "Pal", "email": "pal@gmail.com"},
            {"name": "Ann Lee", "email": "ann@acme.com"},
        ]
    )
    store.replace_verdict_data("t2", data)
    store.save_answer("t1", "Yes", None)
    assert purge(store, frozenset({"gmail.com"})) == (1, 1)
    assert store.thread("t1") is None and store.answer("t1") is None and store.verdict("t1") is None
    assert [c["name"] for c in store.verdicts()["t2"]["contacts"]] == ["Ann Lee"]
