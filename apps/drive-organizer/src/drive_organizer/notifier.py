import html
import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class OrganizerRunStats:
    total_scanned: int = 0
    total_media_sorted: int = 0
    total_docs_classified: int = 0
    total_joint_shortcuts: int = 0
    total_quarantined: int = 0
    actions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class TelegramNotifier:
    """Sends notifications to Telegram bot."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message_sync(self, text: str) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.info("Telegram notifications disabled (missing bot token or chat ID).")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                return True
        except Exception as exc:
            logger.error(f"Failed to dispatch Telegram message: {exc}")
            return False

    def send_summary(self, stats: OrganizerRunStats, dry_run: bool = False) -> bool:
        mode_str = " <i>(DRY RUN)</i>" if dry_run else ""
        lines = [
            f"📂 <b>Google Drive Organizer Report</b>{mode_str}",
            f"• <b>Files Scanned:</b> {stats.total_scanned}",
            f"• <b>Documents Classified:</b> {stats.total_docs_classified}",
            f"• <b>Media Chrono-Sorted:</b> {stats.total_media_sorted}",
            f"• <b>Joint Shortcuts Created:</b> {stats.total_joint_shortcuts}",
        ]

        if stats.total_quarantined > 0:
            lines.append(f"• ⚠️ <b>Needs Review:</b> {stats.total_quarantined}")

        if stats.actions:
            lines.append("\n<b>Recent Actions:</b>")
            for action in stats.actions[-10:]:
                lines.append(f"• {html.escape(action)}")

        if stats.errors:
            lines.append("\n<b>Errors:</b>")
            for err in stats.errors[:5]:
                lines.append(f"• ❌ {html.escape(err)}")

        return self.send_message_sync("\n".join(lines))
