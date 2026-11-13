from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from jobs.extract import Contact, Verdict
from jobs.gmail import Message, Thread


def message(i: int, *, sent: bool = False, days_ago: int = 30, sender: str = "ann@acme.com"):
    when = datetime.now(UTC) - timedelta(days=days_ago)
    return Message(
        id=f"m{i}",
        date=when.isoformat(timespec="seconds"),
        sender_name="Me" if sent else "Ann Lee",
        sender_email="me@example.com" if sent else sender,
        to=["me@example.com"],
        cc=[],
        subject="Senior Engineer role",
        text="Hello",
        sent=sent,
    )


def thread(tid: str, *messages: Message) -> Thread:
    return Thread(id=tid, messages=list(messages))


def verdict(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "kind": "recruiter_outreach",
        "company": "Acme",
        "agency": None,
        "roles": ["Senior Engineer"],
        "contacts": [
            {"name": "Ann Lee", "email": "ann@acme.com", "title": "Recruiter", "role": "recruiter"}
        ],
        "stage": "outreach",
        "summary": "Ann reached out.",
        "confidence": 0.9,
        "doubt": None,
        "options": [],
    }
    base.update(kw)
    return base


class FakeExtractor:
    model = "test:fake"

    def __init__(self) -> None:
        self.answers: list[dict[str, Any] | None] = []

    def __call__(self, t: Thread, answer: dict[str, Any] | None = None) -> Verdict:
        self.answers.append(answer)
        kind = "not_job" if answer and answer.get("choice") == "Not a job contact" else None
        return Verdict(
            kind=kind or "recruiter_outreach",
            company="Acme",
            contacts=[Contact(name="Ann Lee", email="ann@acme.com", role="recruiter")],
            stage="outreach",
            summary="s",
            confidence=0.5,
            doubt="Is this real?",
            options=["Yes", "Not a job contact"],
        )


@pytest.fixture
def fake() -> FakeExtractor:
    return FakeExtractor()
