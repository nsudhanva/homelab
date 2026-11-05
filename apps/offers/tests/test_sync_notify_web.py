from datetime import date

from conftest import txn
from fastapi.testclient import TestClient

from offers.catalog import Catalog
from offers.config import Settings
from offers.models import Account, AIDecision, Candidate, OverrideStatus, State
from offers.notify import notify
from offers.source import Snapshot
from offers.store import Store
from offers.sync import sync
from offers.views import build
from offers.web import account_out, create_app, month_list


class FakeMatcher:
    model = "test-model"

    def __init__(self, decision: AIDecision | None) -> None:
        self.decision = decision
        self.calls: list[str] = []

    def decide(self, candidate: Candidate, offer, card) -> AIDecision | None:
        self.calls.append(candidate.txn.id)
        return self.decision


class FakeSender:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, text: str) -> bool:
        self.messages.append(text)
        return True


def _snapshot(accounts: list[Account]) -> Snapshot:
    return Snapshot(
        accounts,
        [
            txn("t1", "a-gold", date(2026, 11, 2), -12, "Coffee Co"),
            txn("t2", "a-gold", date(2026, 11, 3), -30, "DD *DeliveryDash Thai"),
            txn("t3", "a-gold", date(2026, 11, 4), 13.99, "Streaming Service"),
        ],
    )


def test_sync_asks_ai_once_and_caches(store, catalog, settings, accounts) -> None:
    matcher = FakeMatcher(AIDecision(True, 0.9, "restaurant order"))
    today = date(2026, 11, 5)
    sync(store, catalog, settings, _snapshot(accounts), today, matcher, None)
    sync(store, catalog, settings, _snapshot(accounts), today, matcher, None)
    assert matcher.calls == ["t2"]
    assert {e.offer_id for e in store.evidence()} == {"gold-coffee", "gold-delivery"}


def test_sync_without_ai_leaves_candidates_undecided(store, catalog, settings, accounts) -> None:
    message = sync(store, catalog, settings, _snapshot(accounts), date(2026, 11, 5), None, None)
    assert "1 undecided" in message
    assert not store.review()
    assert "gold-delivery" not in {e.offer_id for e in store.evidence()}


def test_low_confidence_ai_still_decides(store, catalog, settings, accounts) -> None:
    matcher = FakeMatcher(AIDecision(True, 0.5, "maybe a restaurant"))
    sync(store, catalog, settings, _snapshot(accounts), date(2026, 11, 5), matcher, None)
    assert "gold-delivery" in {e.offer_id for e in store.evidence()}
    assert [(i.txn.id, i.offer_id) for i in store.review()] == [("t2", "gold-delivery")]


def test_sync_stops_asking_when_ai_fails(store, catalog, settings, accounts) -> None:
    matcher = FakeMatcher(None)
    sync(store, catalog, settings, _snapshot(accounts), date(2026, 11, 5), matcher, None)
    assert not store.review() and not store.ai_decisions()


def test_notifications_are_sent_once(store, catalog, settings, accounts) -> None:
    sender = FakeSender()
    sync(store, catalog, settings, _snapshot(accounts), date(2026, 11, 27), None, sender)
    assert any("end soon" in m and "Ride cash" in m for m in sender.messages)
    assert not any("review" in m for m in sender.messages)
    count = len(sender.messages)
    assert notify(store, catalog, settings, date(2026, 11, 28), sender) == []
    assert len(sender.messages) == count


def test_monthly_summary(store, catalog, settings, accounts) -> None:
    sync(store, catalog, settings, _snapshot(accounts), date(2026, 11, 5), None, None)
    sender = FakeSender()
    sent = notify(store, catalog, settings, date(2026, 12, 1), sender)
    assert "summary:2026-11" in sent
    summary = next(m for m in sender.messages if "Offers in November 2026" in m)
    assert "Ride cash" in summary


def test_dashboard_view(store, catalog, settings, accounts) -> None:
    sync(store, catalog, settings, _snapshot(accounts), date(2026, 11, 5), None, None)
    board = build(store, catalog, date(2026, 11, 5))
    gold = next(c for c in board.cards if c.account.id == "a-gold")
    states = {r.instance.offer.id: r.state for r in gold.current}
    assert states["gold-coffee"] is State.PENDING
    assert [t.id for t in board.unlinked] == ["t3"]


def test_store_reopens_without_migrating_again(settings: Settings) -> None:
    Store(settings.db_path).close()
    s = Store(settings.db_path)
    assert s.conn.execute("PRAGMA user_version").fetchone()[0] == 1
    s.close()


def test_api_and_actions(store, catalog: Catalog, settings, accounts, tmp_path) -> None:
    matcher = FakeMatcher(AIDecision(True, 0.5, "maybe a restaurant"))
    sync(store, catalog, settings, _snapshot(accounts), date(2026, 11, 5), matcher, None)
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<div id=root></div>")
    client = TestClient(create_app(settings, catalog, web_dist=dist))
    assert client.get("/healthz").text == "ok"
    assert client.get("/review").text == "<div id=root></div>"
    assert client.get("/api/nope").status_code == 404

    assert client.get("/api/dashboard?month=2026-11").json()["months"] == ["2026-11"]
    board = client.get("/api/dashboard").json()
    assert (board["month"], board["as_of"]) == ("2026-11", "2026-11-05")
    gold = next(c for c in board["cards"] if c["account"]["id"] == "a-gold")
    assert gold["card_id"] == "gold"
    states = {o["offer_id"]: o["state"] for o in gold["offers"]}
    assert states["gold-coffee"] == "pending"
    assert [t["id"] for t in board["unlinked"]] == ["t3"]
    assert board["totals"]["to_review"] == 1

    detail = client.get("/api/offers/gold-coffee/a-gold").json()
    assert detail["history"][0]["evidence"][0]["txn"]["payee"] == "Coffee Co"
    assert client.get("/api/offers/nope/a-gold").status_code == 404

    items = client.get("/api/review").json()
    assert [(i["txn"]["id"], i["offer_id"], i["ai_match"]) for i in items] == [
        ("t2", "gold-delivery", True)
    ]
    assert "gold-delivery" in {e.offer_id for e in store.evidence()}
    resp = client.post(
        "/api/review", json={"txn_id": "t2", "offer_id": "gold-delivery", "match": False}
    )
    assert resp.status_code == 204
    assert store.user_decisions() == {("t2", "gold-delivery"): False}
    assert client.get("/api/review").json() == []
    assert "gold-delivery" not in {e.offer_id for e in store.evidence()}

    body = {
        "offer_id": "gold-rides",
        "account_id": "a-gold",
        "period_start": "2026-11-01",
        "status": "used",
    }
    assert client.post("/api/override", json=body).status_code == 204
    assert store.overrides() == {("gold-rides", "a-gold", date(2026, 11, 1)): OverrideStatus.USED}
    assert client.post("/api/override", json={**body, "status": None}).status_code == 204
    assert store.overrides() == {}


def test_account_display_fields() -> None:
    out = account_out(Account("x", "[Pat] Example Card (1234)"))
    assert (out.holder, out.last4) == ("Pat", "1234")
    plain = account_out(Account("y", "Example Card"))
    assert (plain.holder, plain.last4) == (None, None)


def test_history_goes_back_to_the_first_transaction(store, catalog, settings, accounts) -> None:
    old = Snapshot(accounts, [txn("t0", "a-gold", date(2025, 6, 3), -12, "Coffee Co")])
    sync(store, catalog, settings, old, date(2026, 11, 5), None, None)
    from offers.views import all_statuses

    coffee = [
        r
        for r in all_statuses(store, catalog, date(2026, 11, 5))
        if r.instance.offer.id == "gold-coffee"
    ]
    assert coffee[0].window.start == date(2025, 6, 1)
    assert len(coffee) == 18


def test_month_list() -> None:
    assert month_list(date(2026, 11, 20), date(2027, 2, 1)) == [
        "2026-11",
        "2026-12",
        "2027-01",
        "2027-02",
    ]
