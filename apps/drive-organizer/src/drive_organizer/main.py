import argparse
import logging
import sys
import time
from typing import Any

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


def process_single_file(
    file_info: dict[str, Any],
    drive_client: DriveClient,
    classifier: DriveClassifier,
    settings: Settings,
    stats: OrganizerRunStats,
    dry_run: bool,
    folder_breadcrumbs: list[str] | None = None,
) -> bool:
    """Processes, inspects, classifies, moves, and tags a single file."""
    file_id = file_info["id"]
    filename = file_info.get("name", "untitled")
    mime_type = file_info.get("mimeType", "application/octet-stream")
    parents = file_info.get("parents", [])
    created_time = file_info.get("createdTime")
    breadcrumbs = folder_breadcrumbs or file_info.get("folder_breadcrumbs")

    path_desc = f" (Path: {' / '.join(breadcrumbs)})" if breadcrumbs else ""
    logger.info(f"Inspecting '{filename}' (ID: {file_id}, MIME: {mime_type}){path_desc}")

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
            folder_breadcrumbs=breadcrumbs,
        )

        # 2. Handle Media Files (Deterministic datetime organization)
        if inspection.is_media and inspection.media_date:
            dt = inspection.media_date
            target_folder = f"Media/{dt.year}/{dt.year}-{dt.month:02d}"
            logger.info(f"Media file '{filename}' -> {target_folder}")

            if not dry_run:
                target_folder_id = drive_client.get_or_create_path(target_folder)
                drive_client.move_and_tag_file(
                    file_id=file_id,
                    new_name=filename,
                    target_folder_id=target_folder_id,
                    current_parents=parents,
                    description=f"Media photo/video from {dt.strftime('%Y-%m-%d')}",
                    search_tags=["media", str(dt.year)],
                )

            stats.total_media_sorted += 1
            stats.actions.append(f"📷 {filename} → {target_folder}/")
            return True

        # 3. Handle Documents (Classifier with Pydantic AI)
        if inspection.has_extractable_text:
            logger.info(
                f"Extracted {len(inspection.extracted_text)} chars from {inspection.page_count} page(s) of '{filename}'. Submitting to LLM..."
            )
        else:
            logger.info(
                f"No extractable text in '{filename}' ({mime_type}). Submitting metadata to LLM..."
            )

        res = classifier.classify_sync(
            filename=filename,
            extracted_text=inspection.extracted_text,
            mime_type=mime_type,
            folder_breadcrumbs=breadcrumbs,
        )

        target_folder = classifier.resolve_target_folder(res)
        clean_name = res.clean_filename or filename
        logger.info(
            f"LLM Classified '{filename}' -> '{clean_name}' in '{target_folder}' "
            f"(person={res.person}, conf={res.confidence:.2f}, is_joint={res.is_joint})"
        )
        logger.info(f"Summary: {res.summary}")
        logger.info(f"Reasoning: {res.reasoning}")

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

            # Handle Joint Documents: Create full independent copy under spouse folder
            if res.is_joint and res.person in ("Sudhanva", "Maanasa"):
                spouse = "Maanasa" if res.person == "Sudhanva" else "Sudhanva"
                spouse_path = target_folder.replace(f"{res.person}/", f"{spouse}/", 1)
                spouse_folder_id = drive_client.get_or_create_path(spouse_path)
                drive_client.copy_file(
                    file_id=file_id,
                    new_name=clean_name,
                    target_folder_id=spouse_folder_id,
                    description=f"Joint copy for {spouse}: {res.summary}",
                    search_tags=res.search_tags,
                )
                stats.total_joint_shortcuts += 1
                logger.info(f"Created joint copy under {spouse_path}/")

        action_desc = f"📄 {clean_name} → {target_folder}/"
        if res.is_joint:
            spouse = "Maanasa" if res.person == "Sudhanva" else "Sudhanva"
            action_desc += f" (+ Joint Copy in {spouse}/)"
        stats.actions.append(action_desc)

        # Thermal pacing sleep between document inferences
        time.sleep(settings.pacing_seconds)
        return True

    except Exception as exc:
        err_msg = f"Error processing '{filename}': {exc}"
        logger.error(err_msg, exc_info=True)
        stats.errors.append(err_msg)
        return False


def run_pipeline(
    settings: Settings,
    scope: str = "root",
    limit: int | None = None,
    dry_run: bool = False,
) -> OrganizerRunStats:
    """Executes the end-to-end drive organization pipeline."""
    stats = OrganizerRunStats()
    notifier = TelegramNotifier(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        account_name=settings.account_name,
        topic_id=settings.telegram_topic_id,
    )

    if not settings.client_id or not settings.client_secret or not settings.refresh_token:
        err = f"[{settings.account_name}] Missing Google Drive credentials in environment."
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
        timeout_seconds=settings.llm_timeout_seconds,
        primary_llm_provider=settings.primary_llm_provider,
        fallback_llm_provider=settings.fallback_llm_provider,
        openrouter_api_key=settings.openrouter_api_key,
        openrouter_base_url=settings.openrouter_base_url,
        openrouter_model_name=settings.openrouter_model_name,
    )

    # 1. Process loose files in root (or target folder)
    folder_id = "root" if scope == "root" else None
    logger.info(
        f"[{settings.account_name}] Scanning for unprocessed Google Drive files (scope={scope}, folder_id={folder_id}, limit={limit}, dry_run={dry_run})..."
    )
    files = drive_client.list_unprocessed_files(folder_id=folder_id, limit=limit)
    stats.total_scanned += len(files)
    logger.info(f"Found {len(files)} loose file(s) to organize.")

    for idx, file_info in enumerate(files, start=1):
        logger.info(f"[{idx}/{len(files)}] Processing loose file: '{file_info.get('name')}'")
        process_single_file(
            file_info=file_info,
            drive_client=drive_client,
            classifier=classifier,
            settings=settings,
            stats=stats,
            dry_run=dry_run,
        )

    # 2. If scope is root, discover and process unorganized dropped folders
    if scope == "root":
        unorganized_folders = drive_client.list_unorganized_root_folders()
        logger.info(f"Found {len(unorganized_folders)} unorganized folder(s) in My Drive root.")

        for f_idx, folder in enumerate(unorganized_folders, start=1):
            folder_id_val = folder["id"]
            folder_name = folder.get("name", "untitled")
            logger.info(
                f"[{f_idx}/{len(unorganized_folders)}] Evaluating folder '{folder_name}' (ID: {folder_id_val})"
            )

            # Gather manifest and tree summary for LLM triage
            sample_files, tree_summary = drive_client.get_folder_manifest(
                folder_id_val, folder_name
            )
            triage = classifier.triage_folder_sync(folder_name, sample_files, tree_summary)
            logger.info(
                f"Folder '{folder_name}' triage decision: action='{triage.action}', is_code={triage.is_code}, "
                f"target='{triage.target_folder}', conf={triage.confidence:.2f}: {triage.reasoning}"
            )

            if triage.action == "keep_intact":
                target_folder = triage.target_folder or f"Code/{folder_name}"
                logger.info(f"Keeping folder '{folder_name}' intact -> {target_folder}/")
                if not dry_run:
                    drive_client.move_folder_intact(folder_id_val, folder_name, target_folder)
                    drive_client.tag_folder_tree_processed(folder_id_val)
                stats.total_folders_kept_intact += 1
                stats.actions.append(f"📁 Kept intact: '{folder_name}' → {target_folder}/")
            else:
                logger.info(f"Dismantling document batch '{folder_name}'...")
                stats.total_folders_dismantled += 1
                nested_files, folders_to_prune = drive_client.walk_folder_files_and_dirs(
                    folder_id_val, folder_name
                )
                logger.info(
                    f"Found {len(nested_files)} nested file(s) and {len(folders_to_prune)} folder(s) in '{folder_name}'"
                )
                stats.total_scanned += len(nested_files)

                all_files_ok = True
                for n_idx, n_file in enumerate(nested_files, start=1):
                    logger.info(
                        f"[{n_idx}/{len(nested_files)}] Processing nested file: '{n_file.get('name')}'"
                    )
                    ok = process_single_file(
                        file_info=n_file,
                        drive_client=drive_client,
                        classifier=classifier,
                        settings=settings,
                        stats=stats,
                        dry_run=dry_run,
                        folder_breadcrumbs=n_file.get("folder_breadcrumbs"),
                    )
                    if not ok:
                        all_files_ok = False

                if all_files_ok and folders_to_prune:
                    logger.info(
                        f"All files successfully moved from '{folder_name}'. Pruning empty folder shells..."
                    )
                    pruned = drive_client.prune_empty_folders(folders_to_prune, dry_run=dry_run)
                    stats.total_folders_pruned += len(pruned)
                    if pruned:
                        stats.actions.append(
                            f"🗑️ Pruned {len(pruned)} empty folder(s) from '{folder_name}'"
                        )
                elif not all_files_ok:
                    logger.warning(
                        f"Some files in '{folder_name}' encountered errors. Preserving folder shells for safety."
                    )

    logger.info("Pipeline complete. Dispatching summary...")
    notifier.send_summary(stats, dry_run=dry_run)
    return stats


def main() -> None:
    """CLI entrypoint for drive-organizer."""
    parser = argparse.ArgumentParser(description="Google Drive Symmetrical File Organizer")
    parser.add_argument(
        "--scope",
        choices=["root", "all"],
        default="root",
        help="Search scope: 'root' scans files dropped in My Drive root (default), 'all' scans entire drive",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Inspect and classify without mutating Drive"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Maximum number of files to process"
    )
    parser.add_argument("--all", action="store_true", help="Alias for --scope=all")
    parser.add_argument(
        "--account",
        type=str,
        default=None,
        help="Account identifier (e.g. personal, family)",
    )
    args = parser.parse_args()

    scope = "all" if args.all else args.scope

    settings = Settings()
    if args.account:
        settings.account_name = args.account
    stats = run_pipeline(settings=settings, scope=scope, limit=args.limit, dry_run=args.dry_run)

    if stats.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
