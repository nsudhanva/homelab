import httpx
import pytest

from gmail_classifier.notifier import TelegramNotifier


def test_format_daily_summary_single():
    notifier = TelegramNotifier(bot_token="fake-token", chat_id=123)
    quarantined = [
        {
            "subject": "Phishing Attempt?",
            "sender": "spammer@bad.com",
            "confidence": 0.45,
            "reason": "Suspicious link detected",
        }
    ]
    msgs = notifier.format_daily_summary(
        target_date="2026-09-16",
        total_count=10,
        label_counts={"Work": 6, "Personal": 3, "ai-review": 1},
        quarantined_items=quarantined,
        dry_run=False,
    )
    assert len(msgs) == 1
    text = msgs[0]
    assert "Gmail Daily Classifier Summary" in text
    assert "2026-09-16" in text
    assert "Total Processed:</b> 10" in text
    assert "Work</code>: 6" in text
    assert "ai-review</code>: 1" in text
    assert "Phishing Attempt?" in text
    assert "Suspicious link detected (conf: 0.45)" in text


def test_format_daily_summary_with_archived_count():
    notifier = TelegramNotifier(bot_token="fake-token", chat_id=123)
    msgs = notifier.format_daily_summary(
        target_date="2026-09-16",
        total_count=10,
        label_counts={"Personal": 10},
        quarantined_items=[],
        archived_count=42,
    )
    assert len(msgs) == 1
    assert "Archived from Inbox:</b> 42" in msgs[0]


def test_format_daily_summary_dry_run():
    notifier = TelegramNotifier(bot_token="fake-token", chat_id=123)
    msgs = notifier.format_daily_summary(
        target_date="2026-09-16",
        total_count=5,
        label_counts={"Work": 5},
        quarantined_items=[],
        dry_run=True,
    )
    assert len(msgs) == 1
    assert "[DRY RUN]" in msgs[0]


def test_format_daily_summary_chunking():
    notifier = TelegramNotifier(bot_token="fake-token", chat_id=123)
    # Generate large number of quarantined items to force chunking
    quarantined = [
        {
            "subject": f"Suspicious Alert #{i} with very long explanation text",
            "sender": f"alert-{i}@very-long-domain-name.corp.example.com",
            "confidence": 0.25,
            "reason": f"Detailed diagnostic rationale explaining why item #{i} was quarantined.",
        }
        for i in range(50)
    ]
    msgs = notifier.format_daily_summary(
        target_date="2026-09-16",
        total_count=50,
        label_counts={"ai-review": 50},
        quarantined_items=quarantined,
    )
    assert len(msgs) > 1
    for msg in msgs:
        assert len(msg) <= 4096


def test_send_message_missing_token():
    notifier = TelegramNotifier(bot_token=None, chat_id=123)
    # Should safely return True without attempting HTTP
    assert notifier.send_message_sync("Hello") is True


def test_send_message_sync(monkeypatch):
    notifier = TelegramNotifier(bot_token="token123", chat_id=12345)

    def fake_post(self, url, json=None, **kwargs):
        assert "token123" in url
        assert json is not None
        assert json["chat_id"] == 12345
        assert json["text"] == "Test alert"
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    assert notifier.send_message_sync("Test alert") is True


@pytest.mark.asyncio
async def test_send_daily_summary_async(monkeypatch):
    notifier = TelegramNotifier(bot_token="token123", chat_id=12345)

    async def fake_post(self, url, json=None, **kwargs):
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    success = await notifier.send_daily_summary(
        target_date="2026-09-16",
        total_count=1,
        label_counts={"Work": 1},
        quarantined_items=[],
    )
    assert success is True
