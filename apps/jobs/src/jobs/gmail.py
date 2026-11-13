"""Read candidate job threads from Gmail."""

import base64
import hashlib
import logging
import re
import threading
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from email.utils import getaddresses, parseaddr
from html.parser import HTMLParser
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

HIRING_TOOLS = [
    "greenhouse.io",
    "greenhouse-mail.io",
    "lever.co",
    "ashbyhq.com",
    "myworkday.com",
    "myworkdayjobs.com",
    "workday.com",
    "smartrecruiters.com",
    "icims.com",
    "jobvite.com",
    "gem.com",
    "goodtime.io",
    "modernloop.io",
    "calendly.com",
    "paradox.ai",
    "rippling.com",
    "bamboohr.com",
    "breezy.hr",
    "workablemail.com",
    "workable.com",
    "jazzhr.com",
    "recruitee.com",
    "teamtailor.com",
    "taleo.net",
    "successfactors.com",
    "avature.net",
    "eightfold.ai",
    "beamery.com",
    "phenompeople.com",
    "hackerrank.com",
    "codesignal.com",
    "karat.io",
    "karat.com",
    "coderpad.io",
    "hired.com",
    "wellfound.com",
    "angel.co",
    "instahyre.com",
    "naukri.com",
    "hirist.com",
    "cutshort.io",
    "triplebyte.com",
    "otta.com",
    "underdog.io",
    "dover.com",
    "dover.io",
    "fountain.com",
    "hireez.com",
    "seekout.com",
]

_TOOLS = " OR ".join(HIRING_TOOLS)

QUERIES: dict[str, str] = {
    "recruiting": (
        'recruiter OR recruiting OR recruitment OR "talent acquisition" OR "talent partner" '
        'OR "talent team" OR sourcer OR headhunter OR "technical recruiter"'
    ),
    "interview": (
        'interview OR "phone screen" OR "technical screen" OR "recruiter screen" OR onsite '
        'OR "hiring manager" OR "coding challenge" OR "take-home" OR "take home assignment"'
    ),
    "opportunity": (
        '"your background" OR "your profile" OR "your experience" OR "job opportunity" '
        'OR "open role" OR "exciting opportunity" OR "new opportunity" OR "career opportunity" '
        'OR "we are hiring" OR "we\'re hiring" OR "open position" OR "would love to connect" '
        'OR "reaching out"'
    ),
    "hiring-tools": f"from:({_TOOLS})",
    "hiring-tools-mentioned": f"({_TOOLS}) (interview OR application OR candidate)",
    "linkedin": (
        "from:(inmail-hit-reply@linkedin.com OR hit-reply@linkedin.com "
        'OR messages-noreply@linkedin.com OR jobs-noreply@linkedin.com) OR "via LinkedIn"'
    ),
    "invites": (
        "(filename:ics OR subject:invitation OR subject:invite) "
        "(interview OR screen OR chat OR call OR conversation)"
    ),
    "outcome": (
        '"offer letter" OR compensation OR "background check" OR references '
        "OR unfortunately (application OR candidacy OR role)"
    ),
    "sent": (
        "in:sent (resume OR CV OR application OR applying OR applied OR role OR position "
        'OR opportunity OR interview OR recruiter OR "following up" OR "follow up" '
        'OR referral OR hiring OR "job")'
    ),
}

MAX_BODY_CHARS = 4000
_QUOTE_START = re.compile(
    r"^(On .{0,200} wrote:|-----Original Message-----|From: .+|_{5,}|Sent from my )",
    re.MULTILINE,
)


@dataclass
class Message:
    id: str
    date: str
    sender_name: str
    sender_email: str
    to: list[str]
    cc: list[str]
    subject: str
    text: str
    sent: bool
    attachments: list[str] = field(default_factory=list)


@dataclass
class Thread:
    id: str
    messages: list[Message]

    @property
    def subject(self) -> str:
        return self.messages[0].subject if self.messages else ""

    @property
    def first_date(self) -> str:
        return self.messages[0].date if self.messages else ""

    @property
    def last_date(self) -> str:
        return self.messages[-1].date if self.messages else ""

    @property
    def digest(self) -> str:
        ids = ",".join(m.id for m in self.messages)
        return hashlib.sha256(ids.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "messages": [asdict(m) for m in self.messages]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Thread":
        return cls(id=data["id"], messages=[Message(**m) for m in data["messages"]])


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("style", "script", "head"):
            self._skip += 1
        elif tag in ("br", "p", "div", "tr", "li", "h1", "h2", "h3"):
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("style", "script", "head") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _Text()
    parser.feed(html)
    return "".join(parser.parts)


def _decode(data: str | None) -> str:
    if not data:
        return ""
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")


def _calendar_summary(ics: str) -> str:
    keep = ("SUMMARY", "DTSTART", "ORGANIZER", "LOCATION")
    lines = [ln.strip() for ln in ics.splitlines() if ln.split(":", 1)[0].split(";")[0] in keep]
    return "Calendar invite: " + " | ".join(lines[:6]) if lines else ""


def _walk(part: dict[str, Any], out: dict[str, list[str]]) -> None:
    mime = part.get("mimeType", "")
    filename = part.get("filename") or ""
    if filename:
        out["attachments"].append(filename)
    body = part.get("body", {})
    if mime == "text/plain" and not filename:
        out["plain"].append(_decode(body.get("data")))
    elif mime == "text/html" and not filename:
        out["html"].append(_decode(body.get("data")))
    elif mime == "text/calendar" and body.get("data"):
        out["calendar"].append(_calendar_summary(_decode(body.get("data"))))
    for child in part.get("parts", []) or []:
        _walk(child, out)


def clean_body(text: str) -> str:
    match = _QUOTE_START.search(text)
    if match and match.start() > 40:
        text = text[: match.start()]
    lines = [ln.rstrip() for ln in text.splitlines() if not ln.lstrip().startswith(">")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    text = re.sub("[ \\t\u00a0\u200c]{2,}", " ", text)
    return text[:MAX_BODY_CHARS]


def parse_message(raw: dict[str, Any]) -> Message:
    payload = raw.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    parts: dict[str, list[str]] = {"plain": [], "html": [], "calendar": [], "attachments": []}
    _walk(payload, parts)
    body = "\n".join(parts["plain"]).strip() or html_to_text("\n".join(parts["html"]))
    text = "\n".join(filter(None, [*parts["calendar"], clean_body(body)]))
    name, email = parseaddr(headers.get("from", ""))
    when = datetime.fromtimestamp(int(raw.get("internalDate", "0")) / 1000, UTC)
    return Message(
        id=raw["id"],
        date=when.isoformat(timespec="seconds"),
        sender_name=name.strip().strip('"'),
        sender_email=email.lower(),
        to=[a.lower() for _, a in getaddresses([headers.get("to", "")]) if a],
        cc=[a.lower() for _, a in getaddresses([headers.get("cc", "")]) if a],
        subject=headers.get("subject", ""),
        text=text or raw.get("snippet", ""),
        sent="SENT" in raw.get("labelIds", []),
        attachments=parts["attachments"],
    )


def parse_thread(raw: dict[str, Any]) -> Thread:
    messages = [parse_message(m) for m in raw.get("messages", [])]
    messages = [m for m in messages if m.date]
    messages.sort(key=lambda m: m.date)
    return Thread(id=raw["id"], messages=messages)


class Gmail:
    """Thread-safe Gmail reader: one API client per worker thread."""

    def __init__(self, client_id: str, client_secret: str, refresh_token: str) -> None:
        self._credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        self._local = threading.local()

    @property
    def _service(self) -> Any:
        service = getattr(self._local, "service", None)
        if service is None:
            service = build("gmail", "v1", credentials=self._credentials, cache_discovery=False)
            self._local.service = service
        return service

    def _execute(self, request: Any) -> Any:
        for attempt in range(8):
            try:
                return request.execute()
            except HttpError as exc:
                limited = exc.status_code == 403 and "ateLimitExceeded" in str(exc)
                if (limited or exc.status_code in (429, 500, 502, 503)) and attempt < 7:
                    time.sleep(min(60, 2 ** (attempt + 1)))
                    continue
                raise
        raise RuntimeError("unreachable")

    def _list(self, query: str) -> Iterator[str]:
        token: str | None = None
        while True:
            request = (
                self._service.users()
                .messages()
                .list(userId="me", q=query, maxResults=500, pageToken=token)
            )
            result = self._execute(request)
            for item in result.get("messages", []):
                yield item["threadId"]
            token = result.get("nextPageToken")
            if not token:
                return

    def candidate_threads(self, after: date) -> set[str]:
        """Thread IDs that match any job query, from ``after`` on."""
        threads: set[str] = set()
        for name, query in QUERIES.items():
            found = set(self._list(f"after:{after:%Y/%m/%d} ({query})"))
            logger.info(f"query {name}: {len(found)} threads")
            threads |= found
        return threads

    def thread(self, thread_id: str) -> Thread:
        request = self._service.users().threads().get(userId="me", id=thread_id, format="full")
        return parse_thread(self._execute(request))
