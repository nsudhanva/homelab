import html
import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_MAX_MSG_LEN = 4000
TELEGRAM_API_URL = "https://api.telegram.org"


@dataclass
class FiledItem:
    name: str
    folder: str
    confidence: float
    reason: str


@dataclass
class RunReport:
    untagged: int = 0
    dry_run: bool = False
    filed: list[FiledItem] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    error: str | None = None

    def folder_counts(self) -> Counter[str]:
        return Counter(item.folder for item in self.filed)


def _chunks(header: str, lines: list[str]) -> list[str]:
    messages: list[str] = []
    current = header
    for line in lines:
        if len(current) + len(line) + 1 > TELEGRAM_MAX_MSG_LEN:
            messages.append(current.strip())
            current = ""
        current += line + "\n"
    if current.strip():
        messages.append(current.strip())
    return messages


class TelegramNotifier:
    """Sends the run summary to Telegram."""

    def __init__(self, bot_token: str | None, chat_id: int, topic_id: int | None = None) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.topic_id = topic_id

    def format_summary(self, report: RunReport, confidence_threshold: float) -> list[str]:
        badge = " <b>[DRY RUN]</b>" if report.dry_run else ""
        verb = "Would file" if report.dry_run else "Filed"
        header = (
            f"🔐 <b>Bitwarden Organizer</b>{badge}\n"
            f"📥 <b>Items without a folder:</b> {report.untagged}\n"
            f"🗂️ <b>{verb}:</b> {len(report.filed)}\n"
        )
        if report.skipped:
            header += f"⏭️ <b>No valid folder from model:</b> {len(report.skipped)}\n"
        if report.failed:
            header += f"❌ <b>Bitwarden edit failed:</b> {len(report.failed)}\n"
        if report.error:
            header += f"🚨 <b>Run stopped:</b> {html.escape(report.error)}\n"

        lines: list[str] = []
        counts = report.folder_counts()
        if counts:
            lines.append("\n<b>Folders:</b>")
            for folder, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
                lines.append(f"• <code>{html.escape(folder)}</code>: {count}")
        review = [item for item in report.filed if item.confidence < confidence_threshold]
        if review:
            lines.append(f"\n⚠️ <b>Low confidence, check these ({len(review)}):</b>")
            for item in review:
                lines.append(
                    f"• <b>{html.escape(item.name)}</b> → <code>{html.escape(item.folder)}</code>"
                    f" ({item.confidence:.2f})\n  <i>{html.escape(item.reason)}</i>"
                )
        for title, names in (("No valid folder", report.skipped), ("Failed", report.failed)):
            if names:
                lines.append(f"\n<b>{title}:</b>")
                lines.extend(f"• {html.escape(name)}" for name in names)
        return _chunks(header, lines)

    def send_message(self, text: str) -> bool:
        if not self.bot_token:
            logger.info("Telegram bot token not configured. Skipping message dispatch.")
            return True
        payload: dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if self.topic_id is not None:
            payload["message_thread_id"] = self.topic_id
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(
                    f"{TELEGRAM_API_URL}/bot{self.bot_token}/sendMessage", json=payload
                ).raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.error("Failed to send Telegram message: %s", type(exc).__name__)
            return False

    def send_summary(self, report: RunReport, confidence_threshold: float) -> bool:
        results = [
            self.send_message(msg) for msg in self.format_summary(report, confidence_threshold)
        ]
        return all(results)
