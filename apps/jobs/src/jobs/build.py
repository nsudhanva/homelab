"""Group thread verdicts into companies and recruiters."""

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from .config import Settings
from .extract import RELEVANT_KINDS
from .gmail import Thread
from .store import Store

STAGE_ORDER = ["unknown", "outreach", "applied", "screening", "interview", "offer"]
OUTCOMES = {"rejected", "withdrawn"}
SUFFIXES = re.compile(
    r"\b(inc|incorporated|llc|l\.l\.c|ltd|limited|corp|corporation|co|gmbh|plc|pvt|private|"
    r"technologies inc|recruiting|careers|talent|hiring|team)\b\.?",
    re.IGNORECASE,
)
TEAM = re.compile(
    r"\b(team|recruiting|recruitment|talent|careers?|hiring|hr|people ops|staffing|jobs?|"
    r"no-?reply|notifications?)\b",
    re.IGNORECASE,
)
NO_REPLY = re.compile(r"no-?reply|do-?not-?reply|notifications?@|mailer|bounce", re.IGNORECASE)


def company_key(name: str) -> str:
    text = SUFFIXES.sub(" ", name.replace("&", " and "))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def gmail_link(thread_id: str) -> str:
    return f"https://mail.google.com/mail/u/0/#all/{thread_id}"


@dataclass
class Conversation:
    thread_id: str
    subject: str
    first_date: str
    last_date: str
    kind: str
    stage: str
    summary: str
    roles: list[str]
    contacts: list[str]
    company: str
    company_key: str
    agency: str | None
    no_reply: bool
    confidence: float
    doubt: str | None
    options: list[str]
    answered: bool
    link: str


@dataclass
class Recruiter:
    key: str
    name: str
    email: str | None
    title: str | None
    role: str
    company: str
    company_key: str
    agency: str | None
    via: str
    roles: set[str] = field(default_factory=set)
    first_date: str = ""
    last_date: str = ""
    threads: set[str] = field(default_factory=set)


@dataclass
class Company:
    key: str
    name: str
    names: Counter[str] = field(default_factory=Counter)
    agencies: set[str] = field(default_factory=set)
    roles: set[str] = field(default_factory=set)
    recruiters: list[Recruiter] = field(default_factory=list)
    conversations: list[Conversation] = field(default_factory=list)
    stage: str = "unknown"
    outcome: str | None = None
    first_date: str = ""
    last_date: str = ""
    no_reply: bool = False


def _sender_domain_company(thread: Thread) -> str | None:
    for m in thread.messages:
        if not m.sent and m.sender_email and not NO_REPLY.search(m.sender_email):
            domain = m.sender_email.split("@")[-1].split(".")
            if len(domain) >= 2 and domain[-2] not in {"gmail", "yahoo", "outlook", "hotmail"}:
                return domain[-2].capitalize()
    return None


def no_reply(thread: Thread, days: int, today: datetime) -> bool:
    """The owner wrote last, nobody answered, and it has been ``days`` days."""
    if not thread.messages or not thread.messages[-1].sent:
        return False
    last = datetime.fromisoformat(thread.messages[-1].date)
    return today - last >= timedelta(days=days)


def domain(email: str | None) -> str:
    return (email or "").rsplit("@", 1)[-1].lower() if email and "@" in email else ""


def personal_only(thread: Thread, ignored: frozenset[str]) -> bool:
    """Everyone the owner dealt with in the thread uses an ignored domain, such as gmail.com."""
    others = set()
    for m in thread.messages:
        others.update(m.to + m.cc if m.sent else [m.sender_email])
    others.discard("")
    return bool(others) and all(domain(a) in ignored for a in others)


def _merge_dates(obj: Any, first: str, last: str) -> None:
    obj.first_date = min(filter(None, [obj.first_date, first]), default=first)
    obj.last_date = max(obj.last_date, last)


def build(
    threads: list[Thread],
    verdicts: dict[str, dict[str, Any]],
    answers: dict[str, dict[str, Any]],
    renames: dict[str, str],
    no_reply_days: int = 14,
    today: datetime | None = None,
    ignore_domains: frozenset[str] = frozenset(),
) -> tuple[list[Company], list[Conversation]]:
    today = today or datetime.now(UTC)
    companies: dict[str, Company] = {}
    recruiters: dict[str, Recruiter] = {}
    doubts: list[Conversation] = []
    by_name: dict[tuple[str, str], str] = {}
    by_email: dict[tuple[str, str], str] = {}

    for thread in threads:
        v = verdicts.get(thread.id)
        if not v or (ignore_domains and personal_only(thread, ignore_domains)):
            continue
        name = v.get("company") or v.get("agency") or _sender_domain_company(thread)
        relevant = v["kind"] in RELEVANT_KINDS
        if not name and relevant:
            name = "Unknown company"
        key = company_key(name) if name else ""
        display = renames.get(key, name or "")
        if key in renames:
            key = company_key(renames[key]) or key
        conversation = Conversation(
            thread_id=thread.id,
            subject=thread.subject,
            first_date=thread.first_date,
            last_date=thread.last_date,
            kind=v["kind"],
            stage=v.get("stage", "unknown"),
            summary=v.get("summary", ""),
            roles=v.get("roles", []),
            contacts=[
                c["name"]
                for c in v.get("contacts", [])
                if not TEAM.search(c["name"]) and domain(c.get("email")) not in ignore_domains
            ],
            company=display,
            company_key=key,
            agency=v.get("agency"),
            no_reply=relevant and no_reply(thread, no_reply_days, today),
            confidence=v.get("confidence", 0),
            doubt=v.get("doubt"),
            options=v.get("options", []),
            answered=thread.id in answers,
            link=gmail_link(thread.id),
        )
        low = relevant and conversation.confidence < 0.7
        if conversation.doubt or low or conversation.answered:
            doubts.append(conversation)
        if not relevant:
            continue

        company = companies.setdefault(key, Company(key=key, name=display))
        company.names[display] += 1
        if v.get("agency") and v.get("company"):
            company.agencies.add(v["agency"])
        company.roles.update(r for r in v.get("roles", []) if r)
        company.conversations.append(conversation)
        _merge_dates(company, thread.first_date, thread.last_date)
        stage = conversation.stage
        if stage in OUTCOMES:
            company.outcome = stage
        elif STAGE_ORDER.index(stage) > STAGE_ORDER.index(company.stage):
            company.stage = stage

        for c in v.get("contacts", []):
            if TEAM.search(c["name"]) or len(c["name"].split()) > 5:
                continue
            if domain(c.get("email")) in ignore_domains:
                continue
            email = (c.get("email") or "").strip().lower() or None
            if email and NO_REPLY.search(email):
                email = None
            person = " ".join(c["name"].split()).lower()
            rkey = by_email.get((email, key)) if email else None
            rkey = rkey or by_name.get((person, key))
            if rkey is None:
                rkey = f"{key}:{len(recruiters)}"
                recruiters[rkey] = Recruiter(
                    key=rkey,
                    name=" ".join(c["name"].split()),
                    email=email,
                    title=c.get("title"),
                    role=c.get("role", "other"),
                    company=display,
                    company_key=key,
                    agency=v.get("agency") if v.get("company") else None,
                    via=c.get("via", "email"),
                )
            r = recruiters[rkey]
            r.email = r.email or email
            r.title = r.title or c.get("title")
            r.roles.update(x for x in v.get("roles", []) if x)
            r.threads.add(thread.id)
            _merge_dates(r, thread.first_date, thread.last_date)
            if email:
                by_email[(email, key)] = rkey
            by_name[(person, key)] = rkey

    for r in recruiters.values():
        company = companies.get(r.company_key)
        if company:
            company.recruiters.append(r)
    for company in companies.values():
        company.name = company.names.most_common(1)[0][0] if company.names else company.name
        company.no_reply = all(c.no_reply for c in company.conversations)
        if company.outcome and company.stage == "unknown":
            company.stage = "applied"
        company.conversations.sort(key=lambda c: c.last_date, reverse=True)
        company.recruiters.sort(key=lambda r: r.last_date, reverse=True)
    ordered = sorted(companies.values(), key=lambda c: c.last_date, reverse=True)
    doubts.sort(key=lambda c: c.last_date, reverse=True)
    return ordered, doubts


def from_store(store: Store, settings: Settings) -> tuple[list[Company], list[Conversation]]:
    return build(
        store.threads(),
        store.verdicts(),
        store.answers(),
        store.company_names(),
        settings.no_reply_days,
        ignore_domains=settings.ignored_domains,
    )
