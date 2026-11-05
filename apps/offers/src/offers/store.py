"""SQLite storage. The sync job writes the snapshot and the decisions. The web app reads them
and writes user decisions and overrides."""

import sqlite3
import time
from collections.abc import Iterable
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from offers.engine import AIKey, DecisionKey
from offers.models import (
    Account,
    AIDecision,
    Candidate,
    Evidence,
    EvidenceKind,
    OverrideStatus,
    Source,
    Txn,
)

MIGRATIONS = [
    """
    CREATE TABLE accounts (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        closed INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE transactions (
        id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL,
        date TEXT NOT NULL,
        amount_cents INTEGER NOT NULL,
        payee TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT ''
    );
    CREATE INDEX transactions_account_date ON transactions (account_id, date);
    CREATE TABLE evidence (
        offer_id TEXT NOT NULL,
        account_id TEXT NOT NULL,
        period_start TEXT NOT NULL,
        txn_id TEXT NOT NULL,
        kind TEXT NOT NULL,
        source TEXT NOT NULL,
        amount_cents INTEGER NOT NULL,
        confidence REAL NOT NULL,
        reason TEXT NOT NULL,
        PRIMARY KEY (offer_id, account_id, txn_id)
    );
    CREATE TABLE ai_decisions (
        txn_id TEXT NOT NULL,
        offer_id TEXT NOT NULL,
        fingerprint TEXT NOT NULL,
        match INTEGER NOT NULL,
        confidence REAL NOT NULL,
        reason TEXT NOT NULL,
        model TEXT NOT NULL,
        decided_at TEXT NOT NULL,
        PRIMARY KEY (txn_id, offer_id, fingerprint)
    );
    CREATE TABLE user_decisions (
        txn_id TEXT NOT NULL,
        offer_id TEXT NOT NULL,
        match INTEGER NOT NULL,
        decided_at TEXT NOT NULL,
        PRIMARY KEY (txn_id, offer_id)
    );
    CREATE TABLE review (
        txn_id TEXT NOT NULL,
        offer_id TEXT NOT NULL,
        account_id TEXT NOT NULL,
        period_start TEXT NOT NULL,
        kind TEXT NOT NULL,
        confidence REAL NOT NULL,
        reason TEXT NOT NULL,
        PRIMARY KEY (txn_id, offer_id)
    );
    CREATE TABLE overrides (
        offer_id TEXT NOT NULL,
        account_id TEXT NOT NULL,
        period_start TEXT NOT NULL,
        status TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (offer_id, account_id, period_start)
    );
    CREATE TABLE notifications (
        key TEXT PRIMARY KEY,
        sent_at TEXT NOT NULL
    );
    CREATE TABLE runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        status TEXT NOT NULL,
        message TEXT NOT NULL DEFAULT ''
    );
    """,
    """
    ALTER TABLE evidence ADD COLUMN promo_cents INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE review ADD COLUMN ai_match INTEGER NOT NULL DEFAULT 0
    """,
    """
    ALTER TABLE transactions ADD COLUMN category TEXT NOT NULL DEFAULT '';
    CREATE TABLE merchant_types (
        merchant TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        source TEXT NOT NULL,
        confidence REAL NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class ReviewItem:
    txn: Txn
    offer_id: str
    account_id: str
    period_start: date
    kind: EvidenceKind
    confidence: float
    reason: str
    ai_match: bool = False


@dataclass(frozen=True)
class Run:
    started_at: str
    finished_at: str | None
    status: str
    message: str


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, timeout=30, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA busy_timeout = 30000")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def close(self) -> None:
        self.conn.close()

    def _migrate(self) -> None:
        for attempt in range(5):
            try:
                self._migrate_once()
                return
            except sqlite3.OperationalError:
                if attempt == 4:
                    raise
                time.sleep(0.2 * (attempt + 1))

    def _migrate_once(self) -> None:
        with closing(self.conn.cursor()) as cur:
            cur.execute("BEGIN IMMEDIATE")
            try:
                version = cur.execute("PRAGMA user_version").fetchone()[0]
                for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
                    for statement in filter(str.strip, script.split(";")):
                        cur.execute(statement)
                    cur.execute(f"PRAGMA user_version = {number}")
                cur.execute("COMMIT")
            except Exception:
                cur.execute("ROLLBACK")
                raise

    def _write(self, statements: Iterable[tuple[str, tuple | list[tuple]]]) -> None:
        with closing(self.conn.cursor()) as cur:
            cur.execute("BEGIN IMMEDIATE")
            try:
                for sql, params in statements:
                    if isinstance(params, list):
                        cur.executemany(sql, params)
                    else:
                        cur.execute(sql, params)
                cur.execute("COMMIT")
            except Exception:
                cur.execute("ROLLBACK")
                raise

    def replace_snapshot(self, accounts: Iterable[Account], txns: Iterable[Txn]) -> None:
        self._write(
            [
                ("DELETE FROM accounts", ()),
                ("DELETE FROM transactions", ()),
                (
                    "INSERT INTO accounts (id, name, closed) VALUES (?, ?, ?)",
                    [(a.id, a.name, int(a.closed)) for a in accounts],
                ),
                (
                    "INSERT INTO transactions (id, account_id, date, amount_cents, payee,"
                    " description, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [
                        (
                            t.id,
                            t.account_id,
                            t.date.isoformat(),
                            t.amount_cents,
                            t.payee,
                            t.description,
                            t.category,
                        )
                        for t in txns
                    ],
                ),
            ]
        )

    def accounts(self) -> list[Account]:
        rows = self.conn.execute("SELECT id, name, closed FROM accounts ORDER BY name")
        return [Account(r["id"], r["name"], bool(r["closed"])) for r in rows]

    def transactions(self) -> list[Txn]:
        rows = self.conn.execute("SELECT * FROM transactions ORDER BY date")
        return [_txn(r) for r in rows]

    def ai_decisions(self) -> dict[AIKey, AIDecision]:
        rows = self.conn.execute("SELECT * FROM ai_decisions")
        return {
            (r["txn_id"], r["offer_id"], r["fingerprint"]): AIDecision(
                bool(r["match"]), r["confidence"], r["reason"]
            )
            for r in rows
        }

    def save_ai_decision(self, candidate: Candidate, decision: AIDecision, model: str) -> None:
        self._write(
            [
                (
                    "INSERT OR REPLACE INTO ai_decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        candidate.txn.id,
                        candidate.offer_id,
                        candidate.fingerprint,
                        int(decision.match),
                        decision.confidence,
                        decision.reason,
                        model,
                        _now(),
                    ),
                )
            ]
        )

    def user_decisions(self) -> dict[DecisionKey, bool]:
        rows = self.conn.execute("SELECT txn_id, offer_id, match FROM user_decisions")
        return {(r["txn_id"], r["offer_id"]): bool(r["match"]) for r in rows}

    def save_user_decision(self, txn_id: str, offer_id: str, match: bool) -> None:
        self._write(
            [
                (
                    "INSERT OR REPLACE INTO user_decisions VALUES (?, ?, ?, ?)",
                    (txn_id, offer_id, int(match), _now()),
                ),
                ("DELETE FROM review WHERE txn_id = ? AND offer_id = ?", (txn_id, offer_id)),
            ]
        )

    def replace_evidence(self, evidence: Iterable[Evidence]) -> None:
        self._write([("DELETE FROM evidence", ()), (EVIDENCE_INSERT, [_row(e) for e in evidence])])

    def evidence(self) -> list[Evidence]:
        return [
            Evidence(
                offer_id=r["offer_id"],
                account_id=r["account_id"],
                period_start=date.fromisoformat(r["period_start"]),
                txn_id=r["txn_id"],
                kind=EvidenceKind(r["kind"]),
                source=Source(r["source"]),
                amount_cents=r["amount_cents"],
                confidence=r["confidence"],
                reason=r["reason"],
                promo_cents=r["promo_cents"],
            )
            for r in self.conn.execute("SELECT * FROM evidence")
        ]

    def replace_review(self, items: Iterable[tuple[Candidate, AIDecision]]) -> None:
        self._write(
            [
                ("DELETE FROM review", ()),
                (
                    "INSERT OR REPLACE INTO review (txn_id, offer_id, account_id, period_start,"
                    " kind, confidence, reason, ai_match) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        (
                            c.txn.id,
                            c.offer_id,
                            c.account_id,
                            c.period_start.isoformat(),
                            c.kind.value,
                            d.confidence,
                            d.reason,
                            int(d.match),
                        )
                        for c, d in items
                    ],
                ),
            ]
        )

    def review(self) -> list[ReviewItem]:
        rows = self.conn.execute(
            "SELECT r.offer_id, r.account_id, r.period_start, r.kind, r.confidence, r.reason,"
            " r.ai_match,"
            " t.id, t.account_id AS txn_account, t.date, t.amount_cents, t.payee, t.description"
            " FROM review r JOIN transactions t ON t.id = r.txn_id ORDER BY t.date DESC"
        )
        return [
            ReviewItem(
                txn=Txn(
                    r["id"],
                    r["txn_account"],
                    date.fromisoformat(r["date"]),
                    r["amount_cents"],
                    r["payee"],
                    r["description"],
                ),
                offer_id=r["offer_id"],
                account_id=r["account_id"],
                period_start=date.fromisoformat(r["period_start"]),
                kind=EvidenceKind(r["kind"]),
                confidence=r["confidence"],
                reason=r["reason"],
                ai_match=bool(r["ai_match"]),
            )
            for r in rows
        ]

    def overrides(self) -> dict[tuple[str, str, date], OverrideStatus]:
        rows = self.conn.execute("SELECT offer_id, account_id, period_start, status FROM overrides")
        return {
            (r["offer_id"], r["account_id"], date.fromisoformat(r["period_start"])): (
                OverrideStatus(r["status"])
            )
            for r in rows
        }

    def set_override(
        self, offer_id: str, account_id: str, period_start: date, status: OverrideStatus | None
    ) -> None:
        key = (offer_id, account_id, period_start.isoformat())
        if status is None:
            sql = "DELETE FROM overrides WHERE offer_id = ? AND account_id = ? AND period_start = ?"
            self._write([(sql, key)])
            return
        self._write(
            [("INSERT OR REPLACE INTO overrides VALUES (?, ?, ?, ?, ?)", (*key, status, _now()))]
        )

    def was_sent(self, key: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM notifications WHERE key = ?", (key,)).fetchone()
        return row is not None

    def mark_sent(self, key: str) -> None:
        self._write([("INSERT OR IGNORE INTO notifications VALUES (?, ?)", (key, _now()))])

    def start_run(self) -> int:
        cur = self.conn.execute(
            "INSERT INTO runs (started_at, status) VALUES (?, 'running')", (_now(),)
        )
        return int(cur.lastrowid or 0)

    def finish_run(self, run_id: int, status: str, message: str) -> None:
        self._write(
            [
                (
                    "UPDATE runs SET finished_at = ?, status = ?, message = ? WHERE id = ?",
                    (_now(), status, message, run_id),
                )
            ]
        )

    def last_run(self) -> Run | None:
        row = self.conn.execute(
            "SELECT started_at, finished_at, status, message FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return Run(row["started_at"], row["finished_at"], row["status"], row["message"])


EVIDENCE_INSERT = (
    "INSERT OR REPLACE INTO evidence (offer_id, account_id, period_start, txn_id, kind, source,"
    " amount_cents, confidence, reason, promo_cents) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def _row(e: Evidence) -> tuple:
    return (
        e.offer_id,
        e.account_id,
        e.period_start.isoformat(),
        e.txn_id,
        e.kind.value,
        e.source.value,
        e.amount_cents,
        e.confidence,
        e.reason,
        e.promo_cents,
    )


def _txn(row: sqlite3.Row) -> Txn:
    return Txn(
        id=row["id"],
        account_id=row["account_id"],
        date=date.fromisoformat(row["date"]),
        amount_cents=row["amount_cents"],
        payee=row["payee"],
        description=row["description"],
        category=row["category"],
    )
