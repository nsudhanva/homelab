import html
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_MAX_MSG_LEN = 4000
TELEGRAM_API_URL = "https://api.telegram.org"


def _quarantine_entry(item: dict[str, Any]) -> str:
    subj = html.escape(item.get("subject", "(No Subject)"))
    sender = html.escape(item.get("sender", "Unknown"))
    reason = html.escape(item.get("reason", "Unknown reason"))
    conf = item.get("confidence", 0.0)
    return (
        f"• <b>{subj}</b>\n  <i>From:</i> {sender}\n  <i>Reason:</i> {reason} (conf: {conf:.2f})\n"
    )


class TelegramNotifier:
    """Telegram notification client for dispatching daily classification summaries."""

    def __init__(
        self,
        bot_token: str | None,
        chat_id: int,
        topic_id: int | None = None,
        account_name: str = "personal",
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.topic_id = topic_id
        self.account_name = account_name

    def format_daily_summary(
        self,
        target_date: str,
        total_count: int,
        label_counts: dict[str, int],
        quarantined_items: list[dict[str, Any]],
        dry_run: bool = False,
        archived_count: int = 0,
    ) -> list[str]:
        """Format daily summary into one or more HTML messages respecting Telegram limits."""
        acct = self.account_name.title()
        dry_run_badge = " <b>[DRY RUN]</b>" if dry_run else ""
        archived_line = (
            f"📦 <b>Archived from Inbox:</b> {archived_count}\n" if archived_count > 0 else ""
        )
        header = (
            f"📬 <b>Gmail Daily Classifier Summary [{acct}]</b>{dry_run_badge}\n"
            f"📅 <b>Date:</b> <code>{html.escape(target_date)}</code>\n"
            f"🔢 <b>Total Processed:</b> {total_count}\n"
            f"{archived_line}"
        )

        labels_section = "\n🏷️ <b>Label Distribution:</b>\n"
        if label_counts:
            for lbl, count in sorted(label_counts.items(), key=lambda x: (-x[1], x[0])):
                labels_section += f"• <code>{html.escape(lbl)}</code>: {count}\n"
        else:
            labels_section += "• <i>No emails classified</i>\n"

        entries = [_quarantine_entry(item) for item in quarantined_items]
        quarantine_section = ""
        if entries:
            quarantine_section = f"\n⚠️ <b>Quarantined Emails ({len(entries)}):</b>\n" + "".join(
                entries
            )

        full_text = f"{header}{labels_section}{quarantine_section}".strip()

        if len(full_text) <= TELEGRAM_MAX_MSG_LEN:
            return [full_text]

        chunks: list[str] = [f"{header}{labels_section}".strip()]
        curr_chunk = f"⚠️ <b>Quarantined Emails ({len(entries)}):</b>\n"
        for entry in entries:
            if len(curr_chunk) + len(entry) > TELEGRAM_MAX_MSG_LEN:
                chunks.append(curr_chunk.strip())
                curr_chunk = entry
            else:
                curr_chunk += entry

        if curr_chunk.strip():
            chunks.append(curr_chunk.strip())

        return chunks

    def send_message(self, text: str) -> bool:
        if not self.bot_token:
            logger.info("Telegram bot token not configured. Skipping message dispatch.")
            return True

        endpoint = f"{TELEGRAM_API_URL}/bot{self.bot_token}/sendMessage"
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
                resp = client.post(endpoint, json=payload)
                resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error(f"Failed to dispatch Telegram message: {exc}")
            return False

    def send_daily_summary(
        self,
        target_date: str,
        total_count: int,
        label_counts: dict[str, int],
        quarantined_items: list[dict[str, Any]],
        dry_run: bool = False,
        archived_count: int = 0,
    ) -> bool:
        messages = self.format_daily_summary(
            target_date=target_date,
            total_count=total_count,
            label_counts=label_counts,
            quarantined_items=quarantined_items,
            dry_run=dry_run,
            archived_count=archived_count,
        )
        success = True
        for msg in messages:
            if not self.send_message(msg):
                success = False
        return success
