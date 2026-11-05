import logging
from datetime import datetime, timedelta
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .config import Settings

logger = logging.getLogger(__name__)


class GmailClient:
    """Client for interacting with the Gmail API v1."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        processed_label: str = "ai-processed",
        service: Any = None,
    ) -> None:
        self.processed_label = processed_label
        self.service: Any = service

        if self.service is None:
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=["https://www.googleapis.com/auth/gmail.modify"],
            )
            self.service = build("gmail", "v1", credentials=credentials, cache_discovery=False)

    @classmethod
    def from_settings(cls, settings: Settings) -> "GmailClient":
        return cls(
            client_id=settings.gmail_client_id,
            client_secret=settings.gmail_client_secret,
            refresh_token=settings.gmail_refresh_token,
            processed_label=settings.processed_label,
        )

    def get_user_labels(self) -> dict[str, str]:
        """Fetch all labels for the authenticated user and map label names to IDs."""
        res = self.service.users().labels().list(userId="me").execute()
        labels = res.get("labels", [])
        return {lbl["name"]: lbl["id"] for lbl in labels if "name" in lbl and "id" in lbl}

    def ensure_label_exists(self, name: str) -> str:
        """Get or create label by name, returning its label ID."""
        labels = self.get_user_labels()
        if name in labels:
            return labels[name]

        logger.info(f"Label '{name}' not found. Creating label...")
        body = {
            "name": name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        created = self.service.users().labels().create(userId="me", body=body).execute()
        return str(created["id"])

    def _list_ids(self, query: str, limit: int | None = None, **extra: Any) -> list[str]:
        logger.info(f"Listing messages with query: '{query}'")
        messages: list[str] = []
        page_token: str | None = None
        while True:
            res = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, pageToken=page_token, **extra)
                .execute()
            )
            for item in res.get("messages", []):
                if "id" in item:
                    messages.append(item["id"])
                    if limit is not None and len(messages) >= limit:
                        return messages
            page_token = res.get("nextPageToken")
            if not page_token:
                return messages

    def _batch_remove_label(self, message_ids: list[str], label: str, batch_size: int) -> int:
        total = 0
        for i in range(0, len(message_ids), batch_size):
            chunk = message_ids[i : i + batch_size]
            self.service.users().messages().batchModify(
                userId="me", body={"ids": chunk, "removeLabelIds": [label]}
            ).execute()
            total += len(chunk)
            logger.info(f"Removed {label} from {len(chunk)} messages ({total}/{len(message_ids)})")
        return total

    def list_messages_for_date(self, target_date: str) -> list[str]:
        """Query messages within target_date (YYYY-MM-DD) that do not have processed_label."""
        dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        next_day = dt + timedelta(days=1)
        after_str = dt.strftime("%Y/%m/%d")
        before_str = next_day.strftime("%Y/%m/%d")
        return self._list_ids(
            f"after:{after_str} before:{before_str} -label:{self.processed_label}"
        )

    def list_unprocessed_inbox_messages(self, limit: int | None = None) -> list[str]:
        """Query all unprocessed messages currently residing in the user's INBOX."""
        return self._list_ids(f"-label:{self.processed_label} in:inbox", limit)

    def get_message_content(self, msg_id: str) -> dict[str, Any]:
        """Retrieve full message resource including payload and headers."""
        return self.service.users().messages().get(userId="me", id=msg_id, format="full").execute()

    def apply_label(self, msg_id: str, add_label_ids: list[str]) -> dict[str, Any]:
        return (
            self.service.users()
            .messages()
            .modify(userId="me", id=msg_id, body={"addLabelIds": add_label_ids})
            .execute()
        )

    def list_messages_to_archive(
        self, older_than_days: int, quarantine_label: str, limit: int | None = None
    ) -> list[str]:
        """Query emails in INBOX with processed_label, excluding quarantine, older than days."""
        return self._list_ids(
            f"in:inbox label:{self.processed_label} -label:{quarantine_label} "
            f"older_than:{older_than_days}d",
            limit,
        )

    def batch_archive_messages(self, message_ids: list[str], batch_size: int = 1000) -> int:
        """Batch remove INBOX label from multiple messages without modifying other labels."""
        return self._batch_remove_label(message_ids, "INBOX", batch_size)

    def list_unread_messages(self, limit: int | None = None) -> list[str]:
        """List IDs of every unread message outside spam and trash."""
        return self._list_ids("is:unread", limit, maxResults=500)

    def batch_mark_read(self, message_ids: list[str], batch_size: int = 1000) -> int:
        """Batch remove the UNREAD label without modifying other labels."""
        return self._batch_remove_label(message_ids, "UNREAD", batch_size)
