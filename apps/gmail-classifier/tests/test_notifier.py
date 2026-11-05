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
    assert "Gmail Daily Classifier Summary [Personal]" in text
    assert "2026-09-16" in text
    assert "Total Processed:</b> 10" in text
    assert "Work</code>: 6" in text
    assert "ai-review</code>: 1" in text
    assert "Phishing Attempt?" in text
    assert "Suspicious link detected (conf: 0.45)" in text


@pytest.mark.parametrize(
    ("account_name", "options", "expected"),
    [
        pytest.param("family", {}, "Gmail Daily Classifier Summary [Family]", id="account"),
        pytest.param(
            "personal", {"archived_count": 42}, "Archived from Inbox:</b> 42", id="archived"
        ),
        pytest.param("personal", {"dry_run": True}, "[DRY RUN]", id="dry-run"),
    ],
)
def test_format_daily_summary_options(account_name, options, expected):
    notifier = TelegramNotifier(bot_token="fake-token", chat_id=123, account_name=account_name)
    msgs = notifier.format_daily_summary(
        target_date="2026-09-16",
        total_count=3,
        label_counts={"Personal": 3},
        quarantined_items=[],
        **options,
    )
    assert len(msgs) == 1
    assert expected in msgs[0]


def test_format_daily_summary_chunking():
    notifier = TelegramNotifier(bot_token="fake-token", chat_id=123)
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
    assert notifier.send_message("Hello") is True


@pytest.mark.parametrize("topic_id", [None, 99])
def test_send_message(monkeypatch, topic_id):
    notifier = TelegramNotifier(bot_token="token123", chat_id=12345, topic_id=topic_id)
    sent = {}

    def fake_post(self, url, json=None, **kwargs):
        sent.update(url=url, json=json)
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    assert notifier.send_message("Test alert") is True
    assert "token123" in sent["url"]
    assert sent["json"]["chat_id"] == 12345
    assert sent["json"]["text"] == "Test alert"
    if topic_id is None:
        assert "message_thread_id" not in sent["json"]
    else:
        assert sent["json"]["message_thread_id"] == topic_id
