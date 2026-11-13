"""The JSON API and the single-page app. The API reads the store, and writes only review
answers and overrides."""

import re
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from offers import views
from offers.catalog import Catalog, Kind, describe, load_catalog
from offers.config import Settings
from offers.engine import OfferStatus, card_accounts, instances, unlinked_credits
from offers.models import Account, OverrideStatus, Txn
from offers.store import Store

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
    how_to_use: str | None
    account: AccountOut
    period: PeriodOut
    state: str
    captured: float
    remaining: float
    override: str | None


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
    cycle: str
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


class Cell(BaseModel):
    month: str
    offer_id: str | None
    span: int
    state: str | None
    value: float
    captured: float
    remaining: float
    uses: int
    used: int
    period_start: date | None
    period_label: str | None
    days_left: int | None
    current: bool
    elsewhere: int
    data_from: date | None = None
    override: str | None = None


class TrackerRow(BaseModel):
    offer_id: str
    name: str
    cycle: str
    next_reset: date | None
    kind: str
    in_app: bool
    value: float
    period: str
    uses: int
    how_to_use: str | None
    cells: list[Cell]


class FeeOut(BaseModel):
    fee_date: date | None
    anniversary_month: int | None
    source: str | None
    year_start: date | None
    year_end: date | None
    year_captured: float


class RuleOut(BaseModel):
    name: str
    rate: float
    detail: str


class RewardsOut(BaseModel):
    currency: str
    program: str | None
    base: float
    rules: list[RuleOut]
    note: str | None


class TotalOut(BaseModel):
    captured: float
    since: date | None
    months: int


class TrackerCard(BaseModel):
    card_id: str
    name: str
    issuer: str
    annual_fee: float
    account: AccountOut
    year_captured: float
    fee: FeeOut
    rewards: RewardsOut | None = None
    total: TotalOut | None = None
    rows: list[TrackerRow]


class MonthSummary(BaseModel):
    month: str
    available: float
    captured: float
    open: float
    missed: float
    used_count: int
    open_count: int
    ending_soon: int


class TrackerOut(BaseModel):
    today: date
    latest_txn: date | None
    months: list[str]
    current: MonthSummary
    last_run: RunOut | None
    cards: list[TrackerCard]
    captured_total: float = 0
    unmatched_accounts: list[str] = []
    unlinked: list[TxnOut] = []


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
        how_to_use=offer.how_to_use,
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


def month_key(day: date) -> str:
    return f"{day.year}-{day.month:02d}"


def month_start(key: str) -> date:
    year, month = map(int, key.split("-"))
    return date(year, month, 1)


def fee_out(info: views.FeeInfo, captured: float) -> FeeOut:
    return FeeOut(
        fee_date=info.fee_date,
        anniversary_month=info.anniversary_month,
        source=info.source,
        year_start=info.year_start,
        year_end=info.year_end,
        year_captured=captured,
    )


def tracker(store: Store, catalog: Catalog, today: date, months_back: int) -> TrackerOut:
    txns = store.transactions()
    accounts = store.accounts()
    rows = views.all_statuses(store, catalog, today)
    run = store.last_run()
    months = month_list(views.history_start(txns, today), today)[-months_back:] or [
        month_key(today)
    ]
    current_key = month_key(today)

    grouped: dict[tuple[str, str], list[OfferStatus]] = {}
    for r in rows:
        grouped.setdefault((r.instance.offer.id, r.instance.account.id), []).append(r)

    def elsewhere(r: OfferStatus) -> int:
        rule = r.instance.offer.detect.usage
        if rule is None or rule.scope == "any":
            return 0
        return sum(
            1
            for t in txns
            if t.account_id != r.instance.account.id
            and t.amount_cents < 0
            and r.window.contains(t.date)
            and rule.matches((t.payee, t.description), t.amount)
        )

    lines: dict[tuple[str, str, str], list] = {}
    for inst in instances(catalog, accounts):
        lines.setdefault((inst.card.id, inst.account.id, inst.offer.name), []).append(inst)

    by_id = {t.id: t for t in txns}
    fees: dict[tuple[str, str], views.FeeInfo] = {}

    def fee_for(inst) -> views.FeeInfo:
        key = (inst.card.id, inst.account.id)
        if key not in fees:
            fees[key] = views.fee_info(inst.card, inst.account, txns, today)
        return fees[key]

    cards: dict[tuple[str, str], TrackerCard] = {}
    for versions in lines.values():
        inst = max(versions, key=lambda v: v.offer.valid_from or date.min)
        offer = inst.offer
        statuses = [r for v in versions for r in grouped.get((v.offer.id, v.account.id), [])]
        cells: list[Cell] = []
        index = 0
        while index < len(months):
            key = months[index]
            start = month_start(key)
            options = [
                r
                for r in statuses
                if r.window.start <= start < r.window.end
                or (r.window.start > start and month_key(r.window.start) == key)
            ]
            match = max(
                options, key=lambda r: r.instance.offer.valid_from or date.min, default=None
            )
            if match is None:
                cells.append(
                    Cell(
                        month=key,
                        offer_id=None,
                        span=1,
                        state=None,
                        value=0,
                        captured=0,
                        remaining=0,
                        uses=offer.uses,
                        used=0,
                        period_start=None,
                        period_label=None,
                        days_left=None,
                        current=key == current_key,
                        elsewhere=0,
                    )
                )
                index += 1
                continue
            span = 1
            while (
                index + span < len(months) and month_start(months[index + span]) < match.window.end
            ):
                span += 1
            used = 0
            matched = match.instance.offer
            if matched.promos:
                used = sum(1 for e in match.evidence if e.promo_cents)
            elif matched.uses > 1 and matched.value_cents:
                used = round(match.captured_cents * matched.uses / matched.value_cents)
            cells.append(
                Cell(
                    month=key,
                    offer_id=match.instance.offer.id,
                    span=span,
                    state=match.state.value,
                    value=matched.value,
                    captured=match.captured_cents / 100,
                    remaining=match.remaining_cents / 100,
                    uses=matched.uses,
                    used=used,
                    period_start=match.window.start,
                    period_label=match.window.label,
                    days_left=match.window.days_left(today)
                    if match.window.contains(today)
                    else None,
                    current=match.window.contains(today),
                    elsewhere=elsewhere(match),
                    data_from=match.data_from,
                    override=match.override.value if match.override else None,
                )
            )
            index += span
        if all(c.state is None for c in cells):
            continue
        key = (inst.card.id, inst.account.id)
        info = fee_for(inst)
        if key not in cards:
            mine = [
                r
                for r in rows
                if r.instance.account.id == inst.account.id and r.instance.card.id == inst.card.id
            ]
            cards[key] = TrackerCard(
                card_id=inst.card.id,
                name=inst.card.name,
                issuer=inst.card.issuer,
                annual_fee=inst.card.annual_fee,
                account=account_out(inst.account),
                year_captured=sum(
                    r.captured_cents / 100 for r in mine if r.window.start >= date(today.year, 1, 1)
                ),
                fee=fee_out(
                    info,
                    sum(
                        views.captured_between(r, by_id, info.year_start, info.year_end)
                        for r in mine
                    )
                    / 100
                    if info.year_start and info.year_end
                    else 0,
                ),
                rows=[],
            )
        cards[key].rows.append(
            TrackerRow(
                offer_id=offer.id,
                name=offer.name,
                cycle=views.cycle_text(offer, info),
                next_reset=next((r.window.end for r in statuses if r.window.contains(today)), None),
                kind=offer.kind.value,
                in_app=offer.detect.credit is None and offer.kind is Kind.CREDIT,
                value=offer.value,
                period=offer.period.value,
                uses=offer.uses,
                how_to_use=offer.how_to_use,
                cells=cells,
            )
        )

    pairs = card_accounts(catalog, accounts)
    for card, account in pairs:
        key = (card.id, account.id)
        if key in cards:
            continue
        cards[key] = TrackerCard(
            card_id=card.id,
            name=card.name,
            issuer=card.issuer,
            annual_fee=card.annual_fee,
            account=account_out(account),
            year_captured=0,
            fee=fee_out(views.fee_info(card, account, txns, today), 0),
            rows=[],
        )
    order = {(c.id, a.id): i for i, (c, a) in enumerate(pairs)}
    cards = dict(sorted(cards.items(), key=lambda kv: order.get(kv[0], 0)))

    first_seen: dict[str, date] = {}
    for t in txns:
        if t.account_id not in first_seen or t.date < first_seen[t.account_id]:
            first_seen[t.account_id] = t.date
    for (card_id, account_id), tc in cards.items():
        since = first_seen.get(account_id)
        tc.total = TotalOut(
            captured=sum(
                r.captured_cents
                for r in rows
                if r.instance.card.id == card_id and r.instance.account.id == account_id
            )
            / 100,
            since=since,
            months=len(month_list(since, today)) if since else 0,
        )
        program = catalog.card(card_id).rewards
        if program is not None:
            tc.rewards = RewardsOut(
                currency=program.currency,
                program=program.program,
                base=program.base,
                rules=[
                    RuleOut(name=b.name, rate=b.rate, detail=describe(b))
                    for b in program.bonuses
                    if (b.valid_from is None or b.valid_from <= today)
                    and (b.valid_to is None or today <= b.valid_to)
                ],
                note=program.note,
            )

    now = [r for r in rows if r.window.contains(today) and r.instance.offer.kind is Kind.CREDIT]
    last_month = [
        r
        for r in rows
        if r.window.end == month_start(current_key) and r.instance.offer.kind is Kind.CREDIT
    ]
    return TrackerOut(
        today=today,
        latest_txn=max((t.date for t in txns), default=None),
        months=months,
        current=MonthSummary(
            month=current_key,
            available=sum(r.instance.offer.value for r in now),
            captured=sum(r.captured_cents for r in now) / 100,
            open=sum(r.remaining_cents for r in now) / 100,
            missed=sum(r.remaining_cents for r in last_month) / 100,
            used_count=sum(1 for r in now if r.captured_cents > 0),
            open_count=sum(1 for r in now if r.remaining_cents > 0),
            ending_soon=sum(
                1 for r in now if r.remaining_cents > 0 and r.window.days_left(today) <= 7
            ),
        ),
        last_run=RunOut(**run.__dict__) if run else None,
        cards=list(cards.values()),
        captured_total=sum(c.total.captured for c in cards.values() if c.total),
        unmatched_accounts=[
            a.name
            for a in accounts
            if not a.closed
            and a.id not in {x.id for _, x in pairs}
            and not (
                catalog.ignore_accounts
                and re.search(catalog.ignore_accounts, a.name, re.IGNORECASE)
            )
        ],
        unlinked=[
            txn_out(t, {a.id: a for a in accounts})
            for t in unlinked_credits(catalog, accounts, txns, store.evidence())[:20]
        ],
    )


def month_list(first: date, last: date) -> list[str]:
    months = []
    year, month = first.year, first.month
    while (year, month) <= (last.year, last.month):
        months.append(month_key(date(year, month, 1)))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def create_app(
    settings: Settings | None = None,
    catalog: Catalog | None = None,
    web_dist: Path = WEB_DIST,
    clock: Callable[[], date] | None = None,
) -> FastAPI:
    settings = settings or Settings()
    catalog = catalog or load_catalog(settings.catalog_path)
    app = FastAPI(title="Offers", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(GZipMiddleware, minimum_size=500)

    @app.middleware("http")
    async def cache_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        else:
            response.headers.setdefault("Cache-Control", "no-cache")
        return response

    def store() -> Store:
        return Store(settings.db_path)

    def today() -> date:
        return clock() if clock else datetime.now(settings.tz).date()

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        return "ok"

    @app.get("/api/tracker")
    def tracker_view(months: int = 6) -> TrackerOut:
        s = store()
        try:
            return tracker(s, catalog, today(), max(1, min(months, 24)))
        finally:
            s.close()

    @app.get("/api/offers/{offer_id}/{account_id}")
    def offer_detail(offer_id: str, account_id: str) -> OfferDetailOut:
        offer = catalog.offer(offer_id)
        if offer is None:
            raise HTTPException(404, "unknown offer")
        day = today()
        s = store()
        try:
            rows = sorted(
                (
                    r
                    for r in views.all_statuses(s, catalog, day)
                    if r.instance.account.id == account_id
                    and r.instance.card.id == offer.card
                    and r.instance.offer.name == offer.name
                ),
                key=lambda r: r.window.start,
            )
            accounts = {a.id: a for a in s.accounts()}
            txns = {t.id: t for t in s.transactions()}
        finally:
            s.close()
        if not rows:
            raise HTTPException(404, "unknown account for this offer")
        info = views.fee_info(
            rows[0].instance.card, rows[0].instance.account, list(txns.values()), day
        )
        return OfferDetailOut(
            offer_id=offer.id,
            name=offer.name,
            cycle=views.cycle_text(offer, info),
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
                    ai_match=i.ai_match,
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
            from offers.sync import evaluate

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
            periods = {
                (r.instance.offer.id, r.instance.account.id, r.window.start)
                for r in views.all_statuses(s, catalog, today())
            }
            if body.status and (body.offer_id, body.account_id, body.period_start) not in periods:
                raise HTTPException(404, "no such offer period for this account")
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
