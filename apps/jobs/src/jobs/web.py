"""JSON API and single-page app for the jobs tracker."""

import logging
import threading
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .build import Company, Conversation, from_store
from .config import Settings
from .export import status, workbook
from .store import Store

logger = logging.getLogger(__name__)
WEB_DIST = Path(__file__).parent / "web_dist"


class AnswerIn(BaseModel):
    choice: str | None = Field(None, max_length=300)
    comment: str | None = Field(None, max_length=2000)


class RenameIn(BaseModel):
    name: str = Field(max_length=200)


def company_out(c: Company) -> dict[str, Any]:
    return {
        "key": c.key,
        "name": c.name,
        "stage": c.stage,
        "outcome": c.outcome,
        "status": status(c),
        "no_reply": c.no_reply,
        "first_date": c.first_date,
        "last_date": c.last_date,
        "roles": sorted(c.roles),
        "agencies": sorted(c.agencies),
        "conversations": len(c.conversations),
        "open_questions": sum(1 for x in c.conversations if x.doubt and not x.answered),
        "recruiters": [
            {**asdict(r), "roles": sorted(r.roles), "threads": len(r.threads)} for r in c.recruiters
        ],
    }


def conversation_out(x: Conversation, answer: dict[str, Any] | None) -> dict[str, Any]:
    return {**asdict(x), "answer": answer}


class Cache:
    """Rebuilds the grouped view only when the database changes."""

    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        self._lock = threading.Lock()
        self._version: tuple[Any, ...] | None = None
        self._value: tuple[list[Company], list[Conversation]] = ([], [])

    def get(self) -> tuple[list[Company], list[Conversation]]:
        version = self.store.version()
        with self._lock:
            if version != self._version:
                self._value = from_store(self.store, self.settings)
                self._version = version
            return self._value


def _default_extractor() -> Any:
    from .extract import Extractor

    return Extractor()


def create_app(
    settings: Settings | None = None,
    web_dist: Path = WEB_DIST,
    extractor: Callable[[], Any] = _default_extractor,
) -> FastAPI:
    settings = settings or Settings()
    store = Store(settings.db_path)
    cache = Cache(store, settings)
    app = FastAPI(title="Jobs", docs_url=None, redoc_url=None)
    app.add_middleware(GZipMiddleware, minimum_size=500)

    @app.middleware("http")
    async def cache_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = (
                "no-store" if path.startswith("/api") else "no-cache"
            )
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/overview")
    def overview() -> dict[str, Any]:
        companies, doubts = cache.get()
        open_doubts = [d for d in doubts if not d.answered]
        return {
            "last_sync": store.get_meta("last_sync"),
            "totals": {
                "companies": len(companies),
                "recruiters": sum(len(c.recruiters) for c in companies),
                "conversations": sum(len(c.conversations) for c in companies),
                "open_questions": len(open_doubts),
                "no_reply": sum(1 for c in companies if c.no_reply),
            },
            "companies": [company_out(c) for c in companies],
        }

    @app.get("/api/companies/{key}")
    def company(key: str) -> dict[str, Any]:
        companies, _ = cache.get()
        found = next((c for c in companies if c.key == key), None)
        if found is None:
            raise HTTPException(404, "Company not found")
        answers = store.answers()
        return {
            **company_out(found),
            "conversation_list": [
                conversation_out(x, answers.get(x.thread_id)) for x in found.conversations
            ],
        }

    @app.get("/api/questions")
    def questions() -> dict[str, Any]:
        _, doubts = cache.get()
        answers = store.answers()
        return {
            "open": [conversation_out(d, None) for d in doubts if not d.answered],
            "answered": [
                conversation_out(d, answers.get(d.thread_id)) for d in doubts if d.answered
            ],
        }

    @app.get("/api/threads/{thread_id}")
    def thread(thread_id: str) -> dict[str, Any]:
        found = store.thread(thread_id)
        if found is None:
            raise HTTPException(404, "Thread not found")
        return {
            "id": found.id,
            "subject": found.subject,
            "verdict": store.verdict(thread_id),
            "answer": store.answer(thread_id),
            "messages": [
                {
                    "date": m.date,
                    "from": "You" if m.sent else (m.sender_name or m.sender_email),
                    "email": None if m.sent else m.sender_email,
                    "text": m.text[:1500],
                }
                for m in found.messages
            ],
        }

    @app.post("/api/threads/{thread_id}/answer")
    def answer(thread_id: str, body: AnswerIn) -> dict[str, Any]:
        if store.thread(thread_id) is None:
            raise HTTPException(404, "Thread not found")
        if not (body.choice or body.comment):
            raise HTTPException(422, "Give an answer or a comment")
        store.save_answer(thread_id, body.choice, body.comment)
        try:
            from .sync import evaluate_one

            verdict = evaluate_one(store, extractor(), thread_id, settings.ignored_domains)
            return {"saved": True, "applied": True, "verdict": verdict and verdict.model_dump()}
        except Exception as exc:
            logger.warning(f"answer saved, AI update deferred to the next sync: {exc}")
            return {"saved": True, "applied": False, "verdict": None}

    @app.post("/api/companies/{key}/rename")
    def rename(key: str, body: RenameIn) -> dict[str, bool]:
        store.rename_company(key, body.name)
        return {"saved": True}

    @app.get("/api/export.xlsx")
    def export() -> Response:
        companies, doubts = cache.get()
        return Response(
            workbook(companies, doubts),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="recruiters.xlsx"'},
        )

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(404)
        candidate = (web_dist / path).resolve()
        if path and candidate.is_file() and web_dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        index = web_dist / "index.html"
        if not index.is_file():
            raise HTTPException(404, "Web app not built")
        return FileResponse(index)

    return app
