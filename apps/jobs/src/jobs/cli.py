import argparse
import logging
from datetime import date
from pathlib import Path

from .config import Settings
from .store import Store


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="jobs")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Run the web app")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    run = sub.add_parser("sync", help="Fetch new threads from Gmail and classify them")
    run.add_argument("--since", type=date.fromisoformat, help="Start date (YYYY-MM-DD)")
    export = sub.add_parser("export", help="Write the Excel workbook")
    export.add_argument("path", type=Path)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    for noisy in ("httpx", "httpx2"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    settings = Settings()

    if args.command == "serve":
        import uvicorn

        from .web import create_app

        uvicorn.run(create_app(settings), host=args.host, port=args.port, log_level="warning")
        return

    store = Store(settings.db_path)
    if args.command == "export":
        from .build import from_store
        from .export import workbook

        companies, doubts = from_store(store, settings)
        args.path.write_bytes(workbook(companies, doubts))
        print(f"{len(companies)} companies written to {args.path}")
        return

    from .extract import Extractor
    from .gmail import Gmail
    from .sync import sync

    gmail = Gmail(
        settings.gmail_client_id, settings.gmail_client_secret, settings.gmail_refresh_token
    )
    sync(store, gmail, Extractor(), settings, since=args.since)


if __name__ == "__main__":
    main()
