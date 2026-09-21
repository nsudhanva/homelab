import argparse
import concurrent.futures
import html
import logging
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from .classifier import EmailClassifier, LLMConnectionError
from .config import Settings
from .gmail_client import GmailClient
from .notifier import TelegramNotifier
from .sanitizer import sanitize_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gmail_classifier")


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Daily automated Gmail classifier and triage engine.",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date to process in YYYY-MM-DD format (defaults to yesterday UTC).",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Number of days in the past to process sequentially (e.g. --days 7 for last week).",
    )
    parser.add_argument(
        "--inbox",
        action="store_true",
        default=False,
        help="Process all unprocessed messages currently in the user's INBOX.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run classification without modifying Gmail labels.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of messages to process.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="Number of concurrent classification workers (defaults to Settings.concurrency).",
    )
    parser.add_argument(
        "--archive-days",
        type=int,
        default=None,
        help="Override archive age threshold (defaults to Settings.archive_older_than_days).",
    )
    parser.add_argument(
        "--archive-only",
        action="store_true",
        default=False,
        help="Run only the archive sweep for older emails without classifying new emails.",
    )
    return parser.parse_args(args)


def run_archive_sweep(
    settings: Settings,
    gmail: GmailClient | None = None,
    archive_days: int | None = None,
    dry_run: bool = False,
    limit: int | None = None,
) -> int:
    """Archive classified emails in INBOX older than archive_days, protecting quarantine_label."""
    days = archive_days if archive_days is not None else settings.archive_older_than_days
    if not settings.auto_archive_enabled and archive_days is None:
        logger.info("Auto-archiving is disabled in settings.")
        return 0

    if gmail is None:
        gmail = GmailClient(
            client_id=settings.gmail_client_id,
            client_secret=settings.gmail_client_secret,
            refresh_token=settings.gmail_refresh_token,
            processed_label=settings.processed_label,
        )

    logger.info(
        f"Starting archive sweep for classified emails older than {days} days "
        f"(protecting '{settings.quarantine_label}')..."
    )
    archive_ids = gmail.list_messages_to_archive(
        older_than_days=days,
        quarantine_label=settings.quarantine_label,
        limit=limit,
    )
    if not archive_ids:
        logger.info("No eligible emails found for archiving.")
        return 0

    logger.info(f"Found {len(archive_ids)} eligible email(s) to archive from INBOX.")
    if not dry_run:
        archived_count = gmail.batch_archive_messages(archive_ids)
        logger.info(f"Successfully archived {archived_count} email(s) from INBOX.")
        return archived_count

    logger.info(f"[DRY RUN] Would archive {len(archive_ids)} email(s) from INBOX.")
    return len(archive_ids)


def run_pipeline(
    target_date: str | None,
    dry_run: bool,
    limit: int | None,
    settings: Settings,
    gmail: GmailClient | None = None,
    classifier: EmailClassifier | None = None,
    notifier: TelegramNotifier | None = None,
    inbox_mode: bool = False,
    concurrency: int | None = None,
) -> int:
    """Execute classification pipeline for the given date or entire inbox."""
    run_label = "all inbox messages" if inbox_mode else f"date: {target_date}"
    logger.info(f"Starting Gmail classification for {run_label} (dry_run={dry_run})")

    if gmail is None:
        gmail = GmailClient(
            client_id=settings.gmail_client_id,
            client_secret=settings.gmail_client_secret,
            refresh_token=settings.gmail_refresh_token,
            processed_label=settings.processed_label,
        )

    if classifier is None:
        classifier = EmailClassifier(
            base_url=settings.llm_base_url,
            model_name=settings.llm_model,
            confidence_threshold=settings.confidence_threshold,
            quarantine_label=settings.quarantine_label,
            processed_label=settings.processed_label,
            timeout_seconds=settings.llm_timeout_seconds,
            config=settings.to_llm_client_config(),
        )

    if notifier is None:
        notifier = TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        )

    # Fetch and ensure required labels exist
    user_labels = gmail.get_user_labels()
    processed_label_id = gmail.ensure_label_exists(settings.processed_label)
    quarantine_label_id = gmail.ensure_label_exists(settings.quarantine_label)
    user_labels[settings.processed_label] = processed_label_id
    user_labels[settings.quarantine_label] = quarantine_label_id

    candidate_labels = classifier.filter_candidate_labels(user_labels)
    logger.info(f"Active curated user labels ({len(candidate_labels)}): {candidate_labels}")

    # Query unprocessed messages
    if inbox_mode:
        message_ids = gmail.list_unprocessed_inbox_messages(limit=limit)
        total_found = len(message_ids)
        logger.info(f"Found {total_found} unprocessed message(s) in INBOX")
    else:
        assert target_date is not None
        message_ids = gmail.list_messages_for_date(target_date)
        total_found = len(message_ids)
        logger.info(f"Found {total_found} unprocessed message(s) for {target_date}")
        if limit is not None and total_found > limit:
            logger.info(f"Applying limit of {limit} messages (from {total_found})")
            message_ids = message_ids[:limit]

    active_workers = concurrency if concurrency is not None else settings.concurrency
    workers = max(1, min(active_workers, len(message_ids) or 1))
    logger.info(f"Running classification pipeline with {workers} worker thread(s)")

    label_counts: dict[str, int] = {}
    quarantined_items: list[dict[str, Any]] = []
    processed_count = 0
    state_lock = threading.Lock()
    gmail_lock = threading.Lock()
    abort_event = threading.Event()

    def process_message(index: int, msg_id: str) -> None:
        nonlocal processed_count
        if abort_event.is_set():
            return

        logger.info(f"[{index}/{len(message_ids)}] Processing message {msg_id}")
        try:
            with gmail_lock:
                raw_msg = gmail.get_message_content(msg_id)
            email = sanitize_message(raw_msg)
            result = classifier.classify_sync(email, candidate_labels)

            with state_lock:
                label_counts[result.label] = label_counts.get(result.label, 0) + 1
                processed_count += 1
                current_count = processed_count
                logger.info(
                    f"Result for {msg_id}: label='{result.label}', conf={result.confidence:.2f}, "
                    f"reason='{result.reason}'"
                )

                if result.label == settings.quarantine_label:
                    quarantined_items.append(
                        {
                            "id": msg_id,
                            "subject": email.subject,
                            "sender": email.sender,
                            "confidence": result.confidence,
                            "reason": result.reason,
                        }
                    )

            if not dry_run:
                target_label_id = user_labels.get(result.label, quarantine_label_id)
                add_labels = [target_label_id, processed_label_id]
                with gmail_lock:
                    gmail.apply_label(msg_id, add_label_ids=add_labels)
            else:
                logger.info(
                    f"[DRY RUN] Would apply labels {[result.label, settings.processed_label]}"
                )

            with state_lock:
                if inbox_mode and current_count % 25 == 0 and current_count < len(message_ids):
                    logger.info(
                        "Dispatching interim progress checkpoint "
                        f"({current_count}/{len(message_ids)})..."
                    )
                    notifier.send_daily_summary_sync(
                        target_date=f"Inbox Progress ({current_count}/{len(message_ids)})",
                        total_count=current_count,
                        label_counts=dict(label_counts),
                        quarantined_items=list(quarantined_items[-5:]),
                        dry_run=dry_run,
                    )
        except LLMConnectionError as exc:
            abort_event.set()
            logger.critical(
                f"Aborting batch run! LLM infrastructure failure at message {msg_id} "
                f"[{index}/{len(message_ids)}]: {exc}"
            )
            if notifier:
                msg_text = (
                    "⚠️ <b>Gmail Classifier Halted</b>\n"
                    f"LLM server crashed at message [{index}/{len(message_ids)}]:\n"
                    f"<code>{html.escape(str(exc))}</code>\n\n"
                    "<i>Exiting immediately without marking as processed "
                    "for Kubernetes to restart.</i>"
                )
                notifier.send_message_sync(msg_text)
            raise
        except Exception as exc:
            logger.error(f"Failed to process message {msg_id}: {exc}", exc_info=True)
            with state_lock:
                quarantined_items.append(
                    {
                        "id": msg_id,
                        "subject": "Error retrieving message",
                        "sender": "Unknown",
                        "confidence": 0.0,
                        "reason": f"API / Processing error: {exc}",
                    }
                )
                label_counts[settings.quarantine_label] = (
                    label_counts.get(settings.quarantine_label, 0) + 1
                )
                processed_count += 1

    if workers <= 1:
        for index, msg_id in enumerate(message_ids, start=1):
            if abort_event.is_set():
                break
            process_message(index, msg_id)
            if index < len(message_ids) and not abort_event.is_set():
                time.sleep(1.5)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(process_message, index, msg_id)
                for index, msg_id in enumerate(message_ids, start=1)
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except LLMConnectionError:
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise

    # Run archive sweep for older classified messages if enabled
    archived_count = 0
    if settings.auto_archive_enabled and settings.archive_older_than_days > 0:
        try:
            archived_count = run_archive_sweep(
                settings=settings,
                gmail=gmail,
                dry_run=dry_run,
            )
        except Exception as exc:
            logger.error(f"Archive sweep encountered an error: {exc}", exc_info=True)

    # Dispatch final summary notification to Telegram
    final_header = "All Inbox Messages" if inbox_mode else (target_date or "Unknown")
    logger.info("Dispatching summary to Telegram...")
    notifier.send_daily_summary_sync(
        target_date=final_header,
        total_count=len(message_ids),
        label_counts=label_counts,
        quarantined_items=quarantined_items,
        dry_run=dry_run,
        archived_count=archived_count,
    )

    logger.info(
        f"Classification run completed. Total: {len(message_ids)}, "
        f"Quarantined: {len(quarantined_items)}, Archived: {archived_count}"
    )
    return len(message_ids)


def main() -> None:
    """CLI entrypoint."""
    args = parse_arguments()

    try:
        settings = Settings()
    except Exception as exc:
        logger.error(f"Failed to load application settings from environment: {exc}")
        sys.exit(1)

    if args.archive_only:
        try:
            run_archive_sweep(
                settings=settings,
                archive_days=args.archive_days,
                dry_run=args.dry_run,
                limit=args.limit,
            )
        except Exception as exc:
            logger.exception(f"Unhandled error during archive-only sweep: {exc}")
            sys.exit(1)
        return

    if args.inbox:
        try:
            run_pipeline(
                target_date=None,
                dry_run=args.dry_run,
                limit=args.limit,
                settings=settings,
                inbox_mode=True,
                concurrency=args.concurrency,
            )
        except Exception as exc:
            logger.exception(f"Unhandled error during inbox pipeline: {exc}")
            sys.exit(1)
        return

    if args.days:
        today = datetime.now(UTC).date()
        # Dates from (today - N days) up to yesterday
        dates = [(today - timedelta(days=i)).isoformat() for i in range(args.days, 0, -1)]
    elif args.date:
        dates = [args.date]
    else:
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        dates = [yesterday.isoformat()]

    for target_date in dates:
        try:
            run_pipeline(
                target_date=target_date,
                dry_run=args.dry_run,
                limit=args.limit,
                settings=settings,
                concurrency=args.concurrency,
            )
        except Exception as exc:
            logger.exception(f"Unhandled error during pipeline for date {target_date}: {exc}")
            sys.exit(1)


if __name__ == "__main__":
    main()
