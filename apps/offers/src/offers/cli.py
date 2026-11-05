"""Command line: ``offers sync``, ``offers serve``, and ``offers check-catalog``."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from offers.catalog import load_catalog
from offers.config import Settings

logger = logging.getLogger("offers")


def _sync(settings: Settings, args: argparse.Namespace) -> int:
    from offers.ai import OfferMatcher
    from offers.notify import Telegram
    from offers.source import fetch
    from offers.store import Store
    from offers.sync import sync

    catalog = load_catalog(settings.catalog_path)
    today = datetime.now(settings.tz).date()
    store = Store(settings.db_path)
    run_id = store.start_run()
    try:
        snapshot = fetch(settings, today)
        matcher = OfferMatcher() if settings.ai_enabled else None
        sender = None
        if settings.telegram_enabled and not args.no_notify:
            sender = Telegram(settings.telegram_bot_token, settings.telegram_chat_id)
        message = sync(store, catalog, settings, snapshot, today, matcher, sender)
        store.finish_run(run_id, "ok", message)
    except Exception as exc:
        store.finish_run(run_id, "failed", type(exc).__name__)
        logger.exception("Sync failed")
        return 1
    finally:
        store.close()
    logger.info("Sync finished: %s", message)
    return 0


def _serve(settings: Settings, args: argparse.Namespace) -> int:
    import uvicorn

    from offers.web import create_app

    uvicorn.run(create_app(settings), host=args.host, port=args.port, proxy_headers=True)
    return 0


def _check(settings: Settings, args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else settings.catalog_path
    catalog = load_catalog(path)
    print(f"{path}: {len(catalog.cards)} cards, {len(catalog.offers)} offers")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(prog="offers")
    sub = parser.add_subparsers(dest="command", required=True)
    sync_cmd = sub.add_parser("sync", help="Read Actual, match offers, and send reminders")
    sync_cmd.add_argument("--no-notify", action="store_true", help="Do not send Telegram messages")
    sync_cmd.set_defaults(func=_sync)
    serve_cmd = sub.add_parser("serve", help="Run the dashboard")
    serve_cmd.add_argument("--host", default="0.0.0.0")
    serve_cmd.add_argument("--port", type=int, default=8000)
    serve_cmd.set_defaults(func=_serve)
    check_cmd = sub.add_parser("check-catalog", help="Validate the catalog file")
    check_cmd.add_argument("path", nargs="?")
    check_cmd.set_defaults(func=_check)

    args = parser.parse_args(argv)
    return args.func(Settings(), args)


if __name__ == "__main__":
    sys.exit(main())
