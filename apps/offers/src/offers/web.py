"""The dashboard. It reads the store, and writes only user decisions and overrides."""

from datetime import date, datetime
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from offers import views
from offers.catalog import Catalog, load_catalog
from offers.config import Settings
from offers.engine import make_evidence
from offers.models import Candidate, OverrideStatus, Source, State
from offers.store import Store

HERE = Path(__file__).parent

STATE_LABELS = {
    State.CREDITED: "Credited",
    State.PARTIAL: "Partly credited",
    State.PENDING: "Used, credit pending",
    State.USED: "Used",
    State.UNUSED: "Unused",
    State.IGNORED: "Skipped",
    State.TO_ACTIVATE: "Activate",
    State.ACTIVATED: "Activated",
}


def state_label(state: State) -> str:
    return STATE_LABELS[state]


def create_app(settings: Settings | None = None, catalog: Catalog | None = None) -> FastAPI:
    settings = settings or Settings()
    catalog = catalog or load_catalog(settings.catalog_path)
    app = FastAPI(title="Offers", docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.filters["dollars"] = views.dollars
    templates.env.filters["state_label"] = state_label

    def store() -> Store:
        return Store(settings.db_path)

    def today() -> date:
        return datetime.now(settings.tz).date()

    def back(request: Request, fallback: str = "/") -> RedirectResponse:
        target = request.headers.get("referer") or fallback
        if not target.startswith(str(request.base_url)):
            target = fallback
        return RedirectResponse(target, status_code=303)

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        return "ok"

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        s = store()
        try:
            board = views.build(s, catalog, today())
            run = s.last_run()
        finally:
            s.close()
        return templates.TemplateResponse(
            request, "dashboard.html", {"board": board, "run": run, "catalog": catalog}
        )

    @app.get("/offer/{offer_id}/{account_id}", response_class=HTMLResponse)
    def offer_detail(request: Request, offer_id: str, account_id: str) -> HTMLResponse:
        offer = catalog.offer(offer_id)
        if offer is None:
            raise HTTPException(404)
        s = store()
        try:
            rows = [
                r
                for r in views.all_statuses(s, catalog, today())
                if r.instance.offer.id == offer_id and r.instance.account.id == account_id
            ]
            txns = {t.id: t for t in s.transactions()}
        finally:
            s.close()
        if not rows:
            raise HTTPException(404)
        return templates.TemplateResponse(
            request,
            "offer.html",
            {"offer": offer, "rows": list(reversed(rows)), "txns": txns, "today": today()},
        )

    @app.get("/review", response_class=HTMLResponse)
    def review(request: Request) -> HTMLResponse:
        s = store()
        try:
            items = s.review()
            accounts = {a.id: a for a in s.accounts()}
        finally:
            s.close()
        return templates.TemplateResponse(
            request, "review.html", {"items": items, "catalog": catalog, "accounts": accounts}
        )

    @app.post("/review")
    def decide(
        request: Request,
        txn_id: Annotated[str, Form()],
        offer_id: Annotated[str, Form()],
        match: Annotated[bool, Form()],
    ) -> RedirectResponse:
        s = store()
        try:
            item = next(
                (i for i in s.review() if i.txn.id == txn_id and i.offer_id == offer_id), None
            )
            if item is None:
                raise HTTPException(404)
            s.save_user_decision(txn_id, offer_id, match)
            offer = catalog.offer(offer_id)
            if match and offer is not None:
                candidate = Candidate(
                    offer_id,
                    item.account_id,
                    item.period_start,
                    item.txn,
                    item.kind,
                    offer.fingerprint(),
                )
                s.add_evidence(make_evidence(candidate, Source.MANUAL, 1.0, "confirmed"))
        finally:
            s.close()
        return back(request, "/review")

    @app.post("/override")
    def override(
        request: Request,
        offer_id: Annotated[str, Form()],
        account_id: Annotated[str, Form()],
        period_start: Annotated[date, Form()],
        status: Annotated[str, Form()],
    ) -> RedirectResponse:
        if catalog.offer(offer_id) is None:
            raise HTTPException(404)
        value = None if status == "clear" else OverrideStatus(status)
        s = store()
        try:
            s.set_override(offer_id, account_id, period_start, value)
        finally:
            s.close()
        return back(request)

    return app
