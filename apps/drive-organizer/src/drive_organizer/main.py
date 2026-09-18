import argparse
import logging
import sys
import time

from .classifier import DriveClassifier
from .config import Settings
from .drive_client import DriveClient
from .inspector import FileInspector
from .notifier import OrganizerRunStats, TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("drive_organizer")


def run_pipeline(
    settings: Settings,
    limit: int | None = None,
    dry_run: bool = False,
) -> OrganizerRunStats:
    """Executes the end-to-end drive organization pipeline."""
    stats = OrganizerRunStats()
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)

    if not settings.client_id or not settings.client_secret or not settings.refresh_token:
        err = "Missing Google Drive credentials in environment."
        logger.error(err)
        stats.errors.append(err)
        notifier.send_summary(stats, dry_run=dry_run)
        return stats

    drive_client = DriveClient(
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        refresh_token=settings.refresh_token,
        app_property_key=settings.app_property_key,
    )

    classifier = DriveClassifier(
        base_url=settings.llm_base_url,
        model_name=settings.llm_model_name,
        confidence_threshold=settings.confidence_threshold,
    )

    logger.info(
        f"Scanning for unprocessed Google Drive files (limit={limit}, dry_run={dry_run})..."
    )
    files = drive_client.list_unprocessed_files(limit=limit)
    stats.total_scanned = len(files)
    logger.info(f"Found {len(files)} file(s) to organize.")

    for idx, file_info in enumerate(files, start=1):
        file_id = file_info["id"]
        filename = file_info.get("name", "untitled")
        mime_type = file_info.get("mimeType", "application/octet-stream")
        parents = file_info.get("parents", [])
        created_time = file_info.get("createdTime")

        logger.info(
            f"[{idx}/{len(files)}] Inspecting '{filename}' (ID: {file_id}, MIME: {mime_type})"
        )

        try:
            # 1. Download initial bytes for inspection
            file_bytes = drive_client.download_file_header_bytes(
                file_id, mime_type=mime_type, max_bytes=2_000_000
            )
            inspection = FileInspector.inspect_bytes(
                filename=filename,
                mime_type=mime_type,
                file_bytes=file_bytes,
                created_time_str=created_time,
            )

            # 2. Handle Media Files (Deterministic datetime organization)
            if inspection.is_media and inspection.media_date:
                dt = inspection.media_date
                target_folder = f"Media/{dt.year}/{dt.year}-{dt.month:02d}"
                logger.info(f"Media file '{filename}' -> {target_folder}")

                if not dry_run:
                    folder_id = drive_client.get_or_create_path(target_folder)
                    drive_client.move_and_tag_file(
                        file_id=file_id,
                        new_name=filename,
                        target_folder_id=folder_id,
                        current_parents=parents,
                        description=f"Media photo/video from {dt.strftime('%Y-%m-%d')}",
                        search_tags=["media", str(dt.year)],
                    )

                stats.total_media_sorted += 1
                stats.actions.append(f"📷 {filename} &rarr; {target_folder}/")
                continue

            # 3. Handle Documents (Classifier with Pydantic AI)
            res = classifier.classify_sync(
                filename=filename,
                extracted_text=inspection.extracted_text,
                mime_type=mime_type,
            )

            target_folder = classifier.resolve_target_folder(res)
            clean_name = res.clean_filename or filename
            logger.info(
                f"Classified '{filename}' -> '{clean_name}' in '{target_folder}' "
                f"(person={res.person}, conf={res.confidence:.2f}, is_joint={res.is_joint})"
            )

            if res.category == "Review" or res.confidence < settings.confidence_threshold:
                stats.total_quarantined += 1
            else:
                stats.total_docs_classified += 1

            if not dry_run:
                target_folder_id = drive_client.get_or_create_path(target_folder)
                drive_client.move_and_tag_file(
                    file_id=file_id,
                    new_name=clean_name,
                    target_folder_id=target_folder_id,
                    current_parents=parents,
                    description=res.summary,
                    search_tags=res.search_tags,
                )

                # Handle Joint Documents: Create shortcut under Maanasa
                if res.is_joint and res.person == "Sudhanva":
                    # Determine equivalent path under Maanasa
                    maanasa_path = target_folder.replace("Sudhanva/", "Maanasa/", 1)
                    maanasa_folder_id = drive_client.get_or_create_path(maanasa_path)
                    drive_client.create_shortcut(
                        target_id=file_id,
                        shortcut_name=clean_name,
                        target_folder_id=maanasa_folder_id,
                        description=f"Joint shortcut to {clean_name}",
                    )
                    stats.total_joint_shortcuts += 1
                    logger.info(f"Created joint shortcut under {maanasa_path}/")

            action_desc = f"📄 {clean_name} &rarr; {target_folder}/"
            if res.is_joint:
                action_desc += " <i>(+ Joint Shortcut in Maanasa/)</i>"
            stats.actions.append(action_desc)

            # Thermal pacing sleep between document inferences
            time.sleep(settings.pacing_seconds)

        except Exception as exc:
            err_msg = f"Error processing '{filename}': {exc}"
            logger.error(err_msg, exc_info=True)
            stats.errors.append(err_msg)

    logger.info("Pipeline complete. Dispatching summary...")
    notifier.send_summary(stats, dry_run=dry_run)
    return stats


def main() -> None:
    """CLI entrypoint for drive-organizer."""
    parser = argparse.ArgumentParser(description="Google Drive Symmetrical File Organizer")
    parser.add_argument(
        "--dry-run", action="store_true", help="Inspect and classify without mutating Drive"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Maximum number of files to process"
    )
    parser.add_argument(
        "--all", action="store_true", help="Process all available unprocessed files"
    )
    args = parser.parse_args()

    settings = Settings()
    stats = run_pipeline(settings=settings, limit=args.limit, dry_run=args.dry_run)

    if stats.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
