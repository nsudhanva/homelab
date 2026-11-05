"""The JSON API and the single-page app. The API reads the store, and writes only review
answers and overrides."""

import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from offers import views
from offers.catalog import Catalog, load_catalog
from offers.config import Settings
from offers.engine import OfferStatus
from offers.models import Account, OverrideStatus, Txn
from offers.store import Store
from offers.sync import evaluate

WEB_DIST = Path(__file__).parent / "web_dist"
HOLDER = re.compile(r"^\[(?P<holder>[^\]]+)\]\s*")
LAST4 = re.compile(r"\((?P<last4>\d{4})\)\s*$")


class AccountOut(BaseModel):
    id: str
    name: str
    holder: str | None
    last4: str | None


class PeriodOut(BaseModel):
    start: date
    end: date
    label: str
    days_left: int


class StatusOut(BaseModel):
    offer_id: str
    card_id: str
    name: str
    kind: str
    value: float
    uses: int
    enrollment: bool
    how_to_use: str | None
    valid_to: date | None
    account: AccountOut
    period: PeriodOut
    state: str
    captured: float
    remaining: float
    override: str | None
    evidence_count: int


class CardOut(BaseModel):
    card_id: str
    name: str
    issuer: str
    account: AccountOut
    annual_fee: float
    year_captured: float
    year_missed: float
    offers: list[StatusOut]


class TxnOut(BaseModel):
    id: str
    date: date
    amount: float
    payee: str
    description: str
    account: AccountOut | None


class RunOut(BaseModel):
    started_at: str
    finished_at: str | None
    status: str
    message: str


class Totals(BaseModel):
    open_now: float
    captured_now: float
    to_review: int
    captured_year: float
    missed_year: float
    annual_fees: float


class DashboardOut(BaseModel):
    today: date
    as_of: date
    month: str
    months: list[str]
    last_run: RunOut | None
    totals: Totals
    cards: list[CardOut]
    unlinked: list[TxnOut]


class EvidenceOut(BaseModel):
    kind: str
    source: str
    amount: float
    confidence: float
    reason: str
    txn: TxnOut | None


class HistoryRow(BaseModel):
    status: StatusOut
    evidence: list[EvidenceOut]


class OfferDetailOut(BaseModel):
    offer_id: str
    name: str
    card_name: str
    account: AccountOut
    value: float
    period: str
    history: list[HistoryRow]


class ReviewOut(BaseModel):
    txn: TxnOut
    offer_id: str
    offer_name: str
    card_name: str
    kind: str
    ai_match: bool
    confidence: float
    reason: str


class ReviewIn(BaseModel):
    txn_id: str
    offer_id: str
    match: bool


class OverrideIn(BaseModel):
    offer_id: str
    account_id: str
    period_start: date
    status: Literal["used", "ignored"] | None


def account_out(account: Account) -> AccountOut:
    holder = HOLDER.search(account.name)
    last4 = LAST4.search(account.name)
    return AccountOut(
        id=account.id,
        name=account.name,
        holder=holder["holder"] if holder else None,
        last4=last4["last4"] if last4 else None,
    )


def status_out(r: OfferStatus, today: date) -> StatusOut:
    offer = r.instance.offer
    return StatusOut(
        offer_id=offer.id,
        card_id=r.instance.card.id,
        name=offer.name,
        kind=offer.kind.value,
        value=offer.value,
        uses=offer.uses,
        enrollment=offer.enrollment,
        how_to_use=offer.how_to_use,
        valid_to=offer.valid_to,
        account=account_out(r.instance.account),
        period=PeriodOut(
            start=r.window.start,
            end=r.window.end,
            label=r.window.label,
            days_left=r.window.days_left(today),
        ),
        state=r.state.value,
        captured=r.captured_cents / 100,
        remaining=r.remaining_cents / 100,
        override=r.override.value if r.override else None,
        evidence_count=len(r.evidence),
    )


def txn_out(t: Txn, accounts: dict[str, Account]) -> TxnOut:
    account = accounts.get(t.account_id)
    return TxnOut(
        id=t.id,
        date=t.date,
        amount=t.amount,
        payee=t.payee,
        description=t.description,
        account=account_out(account) if account else None,
    )


def month_list(first: date, last: date) -> list[str]:
    months = []
    year, month = first.year, first.month
    while (year, month) <= (last.year, last.month):
        months.append(f"{year}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def create_app(
    settings: Settings | None = None,
    catalog: Catalog | None = None,
    web_dist: Path = WEB_DIST,
) -> FastAPI:
    settings = settings or Settings()
    catalog = catalog or load_catalog(settings.catalog_path)
    app = FastAPI(title="Offers", docs_url=None, redoc_url=None, openapi_url=None)

    def store() -> Store:
        return Store(settings.db_path)

    def today() -> date:
        return datetime.now(settings.tz).date()

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        return "ok"

    @app.get("/api/dashboard")
    def dashboard(month: str | None = None) -> DashboardOut:
        now = today()
        s = store()
        try:
            first = views.history_start(s.transactions(), now)
            months = month_list(first, now)
            selected = month if month in months else months[-1]
            year, number = map(int, selected.split("-"))
            month_end = date(year + number // 12, number % 12 + 1, 1) - timedelta(days=1)
            day = min(now, month_end)
            board = views.build(s, catalog, day)
            run = s.last_run()
        finally:
            s.close()
        cards = [
            CardOut(
                card_id=c.card.id,
                name=c.card_name,
                issuer=c.card.issuer,
                account=account_out(c.account),
                annual_fee=c.annual_fee_cents / 100,
                year_captured=c.year_captured_cents / 100,
                year_missed=c.year_missed_cents / 100,
                offers=[status_out(r, day) for r in c.current],
            )
            for c in board.cards
        ]
        return DashboardOut(
            today=now,
            as_of=day,
            month=selected,
            months=months,
            last_run=RunOut(**run.__dict__) if run else None,
            totals=Totals(
                open_now=board.open_cents / 100,
                captured_now=board.captured_this_period_cents / 100,
                to_review=board.review_count,
                captured_year=sum(c.year_captured for c in cards),
                missed_year=sum(c.year_missed for c in cards),
                annual_fees=sum(c.annual_fee for c in cards),
            ),
            cards=cards,
            unlinked=[txn_out(t, board.accounts) for t in board.unlinked],
        )

    @app.get("/api/offers/{offer_id}/{account_id}")
    def offer_detail(offer_id: str, account_id: str) -> OfferDetailOut:
        offer = catalog.offer(offer_id)
        if offer is None:
            raise HTTPException(404, "unknown offer")
        day = today()
        s = store()
        try:
            rows = [
                r
                for r in views.all_statuses(s, catalog, day)
                if r.instance.offer.id == offer_id and r.instance.account.id == account_id
            ]
            accounts = {a.id: a for a in s.accounts()}
            txns = {t.id: t for t in s.transactions()}
        finally:
            s.close()
        if not rows:
            raise HTTPException(404, "unknown account for this offer")
        return OfferDetailOut(
            offer_id=offer.id,
            name=offer.name,
            card_name=rows[0].instance.card.name,
            account=account_out(rows[0].instance.account),
            value=offer.value,
            period=offer.period.value,
            history=[
                HistoryRow(
                    status=status_out(r, day),
                    evidence=[
                        EvidenceOut(
                            kind=e.kind.value,
                            source=e.source.value,
                            amount=e.amount_cents / 100,
                            confidence=e.confidence,
                            reason=e.reason,
                            txn=txn_out(txns[e.txn_id], accounts) if e.txn_id in txns else None,
                        )
                        for e in r.evidence
                    ],
                )
                for r in reversed(rows)
            ],
        )

    @app.get("/api/review")
    def review() -> list[ReviewOut]:
        s = store()
        try:
            items = s.review()
            accounts = {a.id: a for a in s.accounts()}
            counted = {(e.txn_id, e.offer_id) for e in s.evidence()}
        finally:
            s.close()
        out = []
        for i in items:
            offer = catalog.offer(i.offer_id)
            out.append(
                ReviewOut(
                    txn=txn_out(i.txn, accounts),
                    offer_id=i.offer_id,
                    offer_name=offer.name if offer else i.offer_id,
                    card_name=catalog.card(offer.card).name if offer else "",
                    kind=i.kind.value,
                    ai_match=(i.txn.id, i.offer_id) in counted,
                    confidence=i.confidence,
                    reason=i.reason,
                )
            )
        return out

    @app.post("/api/review", status_code=204)
    def decide(body: ReviewIn) -> Response:
        s = store()
        try:
            item = next(
                (i for i in s.review() if i.txn.id == body.txn_id and i.offer_id == body.offer_id),
                None,
            )
            offer = catalog.offer(body.offer_id)
            if item is None or offer is None:
                raise HTTPException(404, "not in the review list")
            s.save_user_decision(body.txn_id, body.offer_id, body.match)
            evaluate(s, catalog, settings, None)
        finally:
            s.close()
        return Response(status_code=204)

    @app.post("/api/override", status_code=204)
    def override(body: OverrideIn) -> Response:
        if catalog.offer(body.offer_id) is None:
            raise HTTPException(404, "unknown offer")
        s = store()
        try:
            s.set_override(
                body.offer_id,
                body.account_id,
                body.period_start,
                OverrideStatus(body.status) if body.status else None,
            )
        finally:
            s.close()
        return Response(status_code=204)

    if (web_dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(404)
            candidate = (web_dist / path).resolve()
            if path and candidate.is_file() and candidate.is_relative_to(web_dist.resolve()):
                return FileResponse(candidate)
            return FileResponse(web_dist / "index.html")

    return app
