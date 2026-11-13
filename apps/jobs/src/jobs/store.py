"""SQLite storage for threads, AI verdicts, and your answers."""

import json
import sqlite3
import threading
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .gmail import Thread

SCHEMA = """
CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    digest TEXT NOT NULL,
    subject TEXT NOT NULL,
    first_date TEXT NOT NULL,
    last_date TEXT NOT NULL,
    data TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS verdicts (
    thread_id TEXT PRIMARY KEY,
    digest TEXT NOT NULL,
    answer_at TEXT,
    data TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS answers (
    thread_id TEXT PRIMARY KEY,
    choice TEXT,
    comment TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS company_names (
    alias TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False, timeout=30)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(SCHEMA)

    @contextmanager
    def _tx(self) -> Generator[sqlite3.Connection]:
        with self._lock, self._db:
            yield self._db

    def _all(self, sql: str, args: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    def _one(self, sql: str, args: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with self._lock:
            return self._db.execute(sql, args).fetchone()

    def save_thread(self, thread: Thread) -> bool:
        """Store a thread. Returns True when it is new or has new messages."""
        with self._tx() as db:
            row = db.execute("SELECT digest FROM threads WHERE id = ?", (thread.id,)).fetchone()
            if row and row["digest"] == thread.digest:
                return False
            db.execute(
                "INSERT OR REPLACE INTO threads VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    thread.id,
                    thread.digest,
                    thread.subject,
                    thread.first_date,
                    thread.last_date,
                    json.dumps(thread.to_dict()),
                    now(),
                ),
            )
            return True

    def thread(self, thread_id: str) -> Thread | None:
        row = self._one("SELECT data FROM threads WHERE id = ?", (thread_id,))
        return Thread.from_dict(json.loads(row["data"])) if row else None

    def threads(self) -> list[Thread]:
        rows = self._all("SELECT data FROM threads ORDER BY last_date")
        return [Thread.from_dict(json.loads(r["data"])) for r in rows]

    def pending(self) -> list[str]:
        """Threads without a verdict for their current messages or latest answer."""
        rows = self._all("""
            SELECT t.id FROM threads t
            LEFT JOIN verdicts v ON v.thread_id = t.id
            LEFT JOIN answers a ON a.thread_id = t.id
            WHERE v.thread_id IS NULL OR v.digest != t.digest
               OR (a.thread_id IS NOT NULL AND (v.answer_at IS NULL OR v.answer_at < a.created_at))
            ORDER BY t.last_date DESC
            """)
        return [r["id"] for r in rows]

    def save_verdict(
        self, thread: Thread, data: dict[str, Any], model: str, answer_at: str | None
    ) -> None:
        with self._tx() as db:
            db.execute(
                "INSERT OR REPLACE INTO verdicts VALUES (?, ?, ?, ?, ?, ?)",
                (thread.id, thread.digest, answer_at, json.dumps(data), model, now()),
            )

    def verdicts(self) -> dict[str, dict[str, Any]]:
        rows = self._all("SELECT thread_id, data FROM verdicts")
        return {r["thread_id"]: json.loads(r["data"]) for r in rows}

    def verdict(self, thread_id: str) -> dict[str, Any] | None:
        row = self._one("SELECT data FROM verdicts WHERE thread_id = ?", (thread_id,))
        return json.loads(row["data"]) if row else None

    def save_answer(self, thread_id: str, choice: str | None, comment: str | None) -> str:
        stamp = now()
        with self._tx() as db:
            db.execute(
                "INSERT OR REPLACE INTO answers VALUES (?, ?, ?, ?)",
                (thread_id, choice, comment, stamp),
            )
        return stamp

    def answer(self, thread_id: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM answers WHERE thread_id = ?", (thread_id,))
        return dict(row) if row else None

    def answers(self) -> dict[str, dict[str, Any]]:
        rows = self._all("SELECT * FROM answers")
        return {r["thread_id"]: dict(r) for r in rows}

    def company_names(self) -> dict[str, str]:
        rows = self._all("SELECT alias, name FROM company_names")
        return {r["alias"]: r["name"] for r in rows}

    def rename_company(self, alias: str, name: str) -> None:
        with self._tx() as db:
            if name.strip():
                db.execute(
                    "INSERT OR REPLACE INTO company_names VALUES (?, ?)", (alias, name.strip())
                )
            else:
                db.execute("DELETE FROM company_names WHERE alias = ?", (alias,))

    def version(self) -> tuple[Any, ...]:
        row = self._one(
            """
            SELECT (SELECT max(fetched_at) || count(*) FROM threads),
                   (SELECT max(created_at) || count(*) FROM verdicts),
                   (SELECT max(created_at) || count(*) FROM answers),
                   (SELECT group_concat(alias || name) FROM company_names)
            """
        )
        return tuple(row) if row else ()

    def get_meta(self, key: str) -> str | None:
        row = self._one("SELECT value FROM meta WHERE key = ?", (key,))
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        with self._tx() as db:
            db.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, value))
