import io
import logging
from datetime import datetime
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)

FOLDER_MIME = "application/vnd.google-apps.folder"
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"


class DriveClient:
    """Interacts with Google Drive API v3."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        app_property_key: str = "ai_processed",
    ) -> None:
        self.app_property_key = app_property_key
        self.credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )
        self.service = build("drive", "v3", credentials=self.credentials, cache_discovery=False)
        self._folder_cache: dict[str, str] = {}  # "Path/To/Folder" -> folder_id

    def list_unprocessed_files(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Lists files that have not been processed by the organizer."""
        query = (
            f"not appProperties has {{ key='{self.app_property_key}' and value='true' }} "
            "and trashed = false "
            "and 'me' in owners "
            f"and mimeType != '{FOLDER_MIME}'"
        )
        logger.info(f"Querying Drive files with filter: {query}")

        files: list[dict[str, Any]] = []
        page_token = None

        while True:
            resp = (
                self.service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, parents, size, createdTime, imageMediaMetadata)",
                    pageToken=page_token,
                    pageSize=min(limit or 100, 100),
                )
                .execute()
            )
            files.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token or (limit and len(files) >= limit):
                break

        return files[:limit] if limit else files

    def download_file_header_bytes(
        self, file_id: str, mime_type: str = "", max_bytes: int = 5_000_000
    ) -> bytes:
        """Downloads or exports the file stream, capped at max_bytes for fast inspection."""
        try:
            if mime_type.startswith("application/vnd.google-apps."):
                export_mime = "text/csv" if "spreadsheet" in mime_type else "text/plain"
                req = self.service.files().export_media(fileId=file_id, mimeType=export_mime)
            else:
                req = self.service.files().get_media(fileId=file_id)

            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, req, chunksize=1024 * 1024)
            done = False
            while not done and fh.tell() < max_bytes:
                _, done = downloader.next_chunk()
            fh.seek(0)
            return fh.read(max_bytes)
        except Exception as e:
            logger.warning(f"Could not download or export media for {file_id}: {e}")
            return b""

    def get_or_create_folder(self, folder_name: str, parent_id: str = "root") -> str:
        """Retrieves or creates a folder under parent_id."""
        cache_key = f"{parent_id}/{folder_name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        query = (
            f"name = '{folder_name}' and "
            f"'{parent_id}' in parents and "
            f"mimeType = '{FOLDER_MIME}' and "
            "trashed = false"
        )
        resp = (
            self.service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        )
        existing = resp.get("files", [])
        if existing:
            folder_id = existing[0]["id"]
        else:
            body = {
                "name": folder_name,
                "mimeType": FOLDER_MIME,
                "parents": [parent_id],
            }
            created = self.service.files().create(body=body, fields="id").execute()
            folder_id = created["id"]
            logger.info(f"Created Drive folder '{folder_name}' under parent {parent_id}")

        self._folder_cache[cache_key] = folder_id
        return folder_id

    def get_or_create_path(self, relative_path: str) -> str:
        """Recursively resolves or creates a folder path, e.g. 'Sudhanva/USA/Identity'."""
        parts = [p.strip() for p in relative_path.split("/") if p.strip()]
        current_id = "root"
        for part in parts:
            current_id = self.get_or_create_folder(part, current_id)
        return current_id

    def move_and_tag_file(
        self,
        file_id: str,
        new_name: str,
        target_folder_id: str,
        current_parents: list[str],
        description: str,
        search_tags: list[str],
    ) -> None:
        """Atomically moves, renames, and enriches a file with metadata."""
        parents_to_remove = [p for p in current_parents if p != target_folder_id]
        tag_str = " ".join(f"#{t.strip('#')}" for t in search_tags if t)
        full_desc = f"{description}\nTags: {tag_str}".strip()

        body: dict[str, Any] = {
            "name": new_name,
            "description": full_desc,
            "appProperties": {
                self.app_property_key: "true",
                "processed_at": datetime.now().isoformat(),
            },
        }

        update_kwargs: dict[str, Any] = {
            "fileId": file_id,
            "body": body,
            "fields": "id, name, parents, description, appProperties",
        }
        if target_folder_id not in current_parents:
            update_kwargs["addParents"] = target_folder_id
        if parents_to_remove:
            update_kwargs["removeParents"] = ",".join(parents_to_remove)

        self.service.files().update(**update_kwargs).execute()
        logger.info(
            f"Updated file {file_id}: name='{new_name}', moved to folder {target_folder_id}"
        )

    def create_shortcut(
        self,
        target_id: str,
        shortcut_name: str,
        target_folder_id: str,
        description: str = "",
    ) -> str:
        """Creates a Google Drive shortcut pointing to target_id."""
        body = {
            "name": shortcut_name,
            "mimeType": SHORTCUT_MIME,
            "shortcutDetails": {
                "targetId": target_id,
            },
            "parents": [target_folder_id],
            "description": description,
            "appProperties": {
                self.app_property_key: "true",
            },
        }
        res = self.service.files().create(body=body, fields="id, name").execute()
        logger.info(
            f"Created shortcut '{shortcut_name}' in folder {target_folder_id} -> {target_id}"
        )
        return res["id"]

    def copy_file(
        self,
        file_id: str,
        new_name: str,
        target_folder_id: str,
        description: str = "",
        search_tags: list[str] | None = None,
    ) -> str:
        """Creates an independent, standalone duplicate file in target_folder_id."""
        tag_str = " ".join(f"#{t.strip('#')}" for t in search_tags if t) if search_tags else ""
        full_desc = f"{description}\nTags: {tag_str}".strip()

        body = {
            "name": new_name,
            "parents": [target_folder_id],
            "description": full_desc,
            "appProperties": {
                self.app_property_key: "true",
                "is_joint_copy": "true",
                "processed_at": datetime.now().isoformat(),
            },
        }
        res = self.service.files().copy(fileId=file_id, body=body, fields="id, name").execute()
        logger.info(
            f"Created joint file copy '{new_name}' in folder {target_folder_id} (ID: {res['id']})"
        )
        return res["id"]
