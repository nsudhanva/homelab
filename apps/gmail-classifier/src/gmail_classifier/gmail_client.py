import logging
from datetime import datetime, timedelta
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

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
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.processed_label = processed_label
        self.service: Any = service

        if self.service is None:
            credentials = Credentials(
                token=None,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=["https://www.googleapis.com/auth/gmail.modify"],
            )
            self.service = build("gmail", "v1", credentials=credentials, cache_discovery=False)

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

    def list_messages_for_date(self, target_date: str) -> list[str]:
        """Query messages within target_date (YYYY-MM-DD) that do not have processed_label."""
        dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        next_day = dt + timedelta(days=1)
        after_str = dt.strftime("%Y/%m/%d")
        before_str = next_day.strftime("%Y/%m/%d")
        query = f"after:{after_str} before:{before_str} -label:{self.processed_label}"

        logger.info(f"Listing messages with query: '{query}'")
        messages: list[str] = []
        page_token: str | None = None
        while True:
            req = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    pageToken=page_token,
                )
            )
            res = req.execute()
            for item in res.get("messages", []):
                if "id" in item:
                    messages.append(item["id"])
            page_token = res.get("nextPageToken")
            if not page_token:
                break
        return messages

    def list_unprocessed_inbox_messages(self, limit: int | None = None) -> list[str]:
        """Query all unprocessed messages currently residing in the user's INBOX."""
        query = f"-label:{self.processed_label} in:inbox"
        logger.info(f"Listing all unprocessed inbox messages with query: '{query}'")
        messages: list[str] = []
        page_token: str | None = None
        while True:
            req = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    pageToken=page_token,
                )
            )
            res = req.execute()
            for item in res.get("messages", []):
                if "id" in item:
                    messages.append(item["id"])
                    if limit is not None and len(messages) >= limit:
                        return messages
            page_token = res.get("nextPageToken")
            if not page_token:
                break
        return messages

    def get_message_content(self, msg_id: str) -> dict[str, Any]:
        """Retrieve full message resource including payload and headers."""
        return (
            self.service.users()
            .messages()
            .get(
                userId="me",
                id=msg_id,
                format="full",
            )
            .execute()
        )

    def apply_label(
        self,
        msg_id: str,
        add_label_ids: list[str],
        remove_label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add and/or remove labels on a specific Gmail message."""
        body: dict[str, Any] = {"addLabelIds": add_label_ids}
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids
        return (
            self.service.users()
            .messages()
            .modify(
                userId="me",
                id=msg_id,
                body=body,
            )
            .execute()
        )

    def list_messages_to_archive(
        self,
        older_than_days: int = 90,
        quarantine_label: str = "ai-review",
        limit: int | None = None,
    ) -> list[str]:
        """Query emails in INBOX with processed_label, excluding quarantine, older than days."""
        query = (
            f"in:inbox label:{self.processed_label} -label:{quarantine_label} "
            f"older_than:{older_than_days}d"
        )
        logger.info(f"Listing messages to archive with query: '{query}'")
        messages: list[str] = []
        page_token: str | None = None
        while True:
            req = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    pageToken=page_token,
                )
            )
            res = req.execute()
            for item in res.get("messages", []):
                if "id" in item:
                    messages.append(item["id"])
                    if limit is not None and len(messages) >= limit:
                        return messages
            page_token = res.get("nextPageToken")
            if not page_token:
                break
        return messages

    def batch_archive_messages(self, message_ids: list[str], batch_size: int = 1000) -> int:
        """Batch remove INBOX label from multiple messages without modifying other labels."""
        if not message_ids:
            return 0
        total_archived = 0
        for i in range(0, len(message_ids), batch_size):
            chunk = message_ids[i : i + batch_size]
            body = {
                "ids": chunk,
                "removeLabelIds": ["INBOX"],
            }
            self.service.users().messages().batchModify(userId="me", body=body).execute()
            total_archived += len(chunk)
            logger.info(
                f"Archived batch of {len(chunk)} messages ({total_archived}/{len(message_ids)})"
            )
        return total_archived
