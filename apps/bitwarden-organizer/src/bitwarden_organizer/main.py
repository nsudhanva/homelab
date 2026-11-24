import argparse
import logging
import sys

from homelab_ai import LLMConnectionError

from .bw_client import BitwardenCLI, BitwardenError
from .classifier import FolderClassifier
from .config import Settings
from .items import render_folder_guide, summarize, untagged_items
from .notifier import FiledItem, RunReport, TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
for noisy_logger in ("httpx", "httpx2", "httpcore"):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)
logger = logging.getLogger("bitwarden_organizer")


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="File Bitwarden items without a folder into the existing folders.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify the items without changing Bitwarden.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of items to process (defaults to Settings.max_items).",
    )
    return parser.parse_args(args)


def organize(
    cli: BitwardenCLI,
    classifier: FolderClassifier,
    settings: Settings,
    dry_run: bool = False,
    limit: int | None = None,
) -> RunReport:
    """Log in, file the items without a folder, and lock the vault again."""
    report = RunReport(dry_run=dry_run)
    cli.login(
        settings.bw_client_id.get_secret_value(),
        settings.bw_client_secret.get_secret_value(),
    )
    session = cli.unlock(settings.bw_password.get_secret_value())
    try:
        cli.sync(session)
        folders = cli.list_folders(session)
        items = cli.list_items(session)
        pending = untagged_items(items)
        report.untagged = len(pending)
        logger.info(
            "%d folders, %d items, %d without a folder", len(folders), len(items), len(pending)
        )
        if not pending or not folders:
            return report

        guide = render_folder_guide(folders, items, settings.examples_per_folder)
        batch = pending[: limit or settings.max_items]
        for index, item in enumerate(batch, start=1):
            summary = summarize(item)
            try:
                decision = classifier.classify(summary, folders, guide)
            except LLMConnectionError as exc:
                report.error = "No model answered"
                logger.error("Stopping at item %d/%d: %s", index, len(batch), exc)
                break
            if decision is None:
                report.skipped.append(summary.name)
                continue
            if not dry_run:
                try:
                    cli.set_folder(session, item, decision.folder.id)
                except BitwardenError as exc:
                    logger.error("Could not move item %s: %s", summary.id, exc)
                    report.failed.append(summary.name)
                    continue
            report.filed.append(
                FiledItem(
                    name=summary.name,
                    folder=decision.folder.name,
                    confidence=decision.confidence,
                    reason=decision.reason,
                )
            )
            logger.info(
                "[%d/%d] %s -> %s (%.2f)",
                index,
                len(batch),
                summary.name,
                decision.folder.name,
                decision.confidence,
            )
        if not dry_run and report.filed:
            cli.sync(session)
    finally:
        cli.lock()
    return report


def main() -> None:
    args = parse_arguments()
    try:
        settings = Settings()
    except Exception as exc:
        logger.error("Failed to load settings from the environment: %s", type(exc).__name__)
        sys.exit(1)

    cli = BitwardenCLI(
        binary=settings.bw_binary,
        appdata_dir=settings.bw_appdata_dir,
        server=settings.bw_server,
        timeout=settings.bw_timeout_seconds,
    )
    token = settings.telegram_bot_token
    notifier = TelegramNotifier(
        bot_token=token.get_secret_value() if token else None,
        chat_id=settings.telegram_chat_id,
        topic_id=settings.telegram_topic_id,
    )
    try:
        report = organize(cli, FolderClassifier(), settings, args.dry_run, args.limit)
    except BitwardenError as exc:
        logger.error("Bitwarden error: %s", exc)
        notifier.send_summary(RunReport(error=str(exc)), settings.confidence_threshold)
        sys.exit(1)

    logger.info(
        "Done: %d filed, %d skipped, %d failed of %d without a folder",
        len(report.filed),
        len(report.skipped),
        len(report.failed),
        report.untagged,
    )
    if report.untagged or report.error:
        notifier.send_summary(report, settings.confidence_threshold)
    if report.error:
        sys.exit(1)


if __name__ == "__main__":
    main()
