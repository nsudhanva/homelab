"""Telegram reminders. Each message has a key, and the store records sent keys, so a daily run
never sends the same reminder twice."""

import html
import logging
from datetime import date, timedelta
from typing import Protocol

import httpx

from offers.catalog import Catalog
from offers.config import Settings
from offers.models import State
from offers.store import Store
from offers.views import all_statuses, dollars

logger = logging.getLogger(__name__)


class Sender(Protocol):
    def send(self, text: str) -> bool: ...


class Telegram:
    def __init__(self, bot_token: str, chat_id: str, client: httpx.Client | None = None) -> None:
        self.url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.chat_id = chat_id
        self.client = client or httpx.Client(timeout=10)

    def send(self, text: str) -> bool:
        try:
            resp = self.client.post(
                self.url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            resp.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.error("Telegram send failed: %s", type(exc).__name__)
            return False


def _label(account_name: str, offer_name: str) -> str:
    return f"{html.escape(offer_name)} <i>({html.escape(account_name)})</i>"


def notify(
    store: Store, catalog: Catalog, settings: Settings, today: date, sender: Sender
) -> list[str]:
    """Send the due messages. Returns the keys of the messages sent."""
    rows = all_statuses(store, catalog, today)
    link = f'\n\n<a href="{settings.public_url}">Open the offers dashboard</a>'
    sent: list[str] = []

    def is_due(r) -> bool:
        if not r.window.contains(today):
            return False
        if r.state is State.TO_ACTIVATE:
            return (today - r.window.start).days < settings.reminder_days
        return (
            r.state in (State.UNUSED, State.PARTIAL)
            and r.window.days_left(today) <= settings.reminder_days
        )

    due = [r for r in rows if is_due(r)]
    fresh = []
    for r in due:
        key = f"remind:{r.instance.offer.id}:{r.instance.account.id}:{r.window.start}"
        if not store.was_sent(key):
            fresh.append((key, r))
    if fresh:
        lines = ["<b>Offers that end soon</b>"]
        for _, r in sorted(fresh, key=lambda item: item[1].window.end):
            left = r.window.days_left(today)
            what = (
                "activate" if r.state is State.TO_ACTIVATE else f"{dollars(r.remaining_cents)} left"
            )
            lines.append(
                f"- {_label(r.instance.account.name, r.instance.offer.name)}: {what}, "
                f"{left} day{'s' if left != 1 else ''} to go"
            )
        if sender.send("\n".join(lines) + link):
            for key, _ in fresh:
                store.mark_sent(key)
                sent.append(key)

    last_month_end = date(today.year, today.month, 1)
    last_month = last_month_end - timedelta(days=1)
    summary_key = f"summary:{last_month:%Y-%m}"
    if today.day <= 3 and not store.was_sent(summary_key):
        ended = [r for r in rows if r.window.end == last_month_end]
        if ended:
            captured = sum(r.captured_cents for r in ended)
            missed = [r for r in ended if r.remaining_cents > 0]
            lines = [
                f"<b>Offers in {last_month:%B %Y}</b>",
                f"Captured: {dollars(captured)}",
                f"Missed: {dollars(sum(r.remaining_cents for r in missed))}",
            ]
            lines += [
                f"- {_label(r.instance.account.name, r.instance.offer.name)}: "
                f"{dollars(r.remaining_cents)}"
                for r in missed
            ]
            year = sum(r.captured_cents for r in rows if r.window.end <= last_month_end)
            lines.append(f"Captured this year: {dollars(year)}")
            if sender.send("\n".join(lines) + link):
                store.mark_sent(summary_key)
                sent.append(summary_key)

    return sent
