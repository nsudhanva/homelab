from unittest.mock import MagicMock

from gmail_classifier.classifier import ClassificationResult
from gmail_classifier.config import Settings
from gmail_classifier.main import parse_arguments, run_pipeline


def test_parse_arguments():
    # Defaults
    args = parse_arguments([])
    assert args.date is None
    assert args.days is None
    assert args.dry_run is False
    assert args.limit is None

    # Custom flags
    args = parse_arguments(["--date", "2026-09-15", "--days", "7", "--dry-run", "--limit", "10"])
    assert args.date == "2026-09-15"
    assert args.days == 7
    assert args.dry_run is True
    assert args.limit == 10


def test_run_pipeline_normal(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
    settings = Settings()

    mock_gmail = MagicMock()
    mock_gmail.get_user_labels.return_value = {
        "Work": "lbl-work",
        "Finance": "lbl-finance",
        "ai-processed": "lbl-proc",
        "ai-review": "lbl-rev",
    }
    mock_gmail.ensure_label_exists.side_effect = lambda name: f"lbl-{name}"
    mock_gmail.list_messages_for_date.return_value = ["msg-1", "msg-2"]
    mock_gmail.get_message_content.side_effect = [
        {"id": "msg-1", "snippet": "Work project update"},
        {"id": "msg-2", "snippet": "Spam or unknown"},
    ]

    mock_classifier = MagicMock()
    mock_classifier.filter_candidate_labels.return_value = ["Finance", "Work"]
    mock_classifier.classify_sync.side_effect = [
        ClassificationResult(label="Work", confidence=0.92, reason="Work update"),
        ClassificationResult(label="ai-review", confidence=0.50, reason="Low confidence"),
    ]

    mock_notifier = MagicMock()

    processed_count = run_pipeline(
        target_date="2026-09-16",
        dry_run=False,
        limit=None,
        settings=settings,
        gmail=mock_gmail,
        classifier=mock_classifier,
        notifier=mock_notifier,
    )

    assert processed_count == 2
    assert mock_gmail.apply_label.call_count == 2
    # Check first message: should apply Work and ai-processed
    mock_gmail.apply_label.assert_any_call("msg-1", add_label_ids=["lbl-work", "lbl-ai-processed"])
    # Check second message: should apply ai-review and ai-processed
    mock_gmail.apply_label.assert_any_call(
        "msg-2", add_label_ids=["lbl-ai-review", "lbl-ai-processed"]
    )
    # Check notifier
    mock_notifier.send_daily_summary_sync.assert_called_once()
    call_kwargs = mock_notifier.send_daily_summary_sync.call_args.kwargs
    assert call_kwargs["total_count"] == 2
    assert call_kwargs["label_counts"] == {"Work": 1, "ai-review": 1}
    assert len(call_kwargs["quarantined_items"]) == 1


def test_run_pipeline_dry_run(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
    settings = Settings()

    mock_gmail = MagicMock()
    mock_gmail.get_user_labels.return_value = {"Work": "lbl-work"}
    mock_gmail.ensure_label_exists.side_effect = lambda name: f"lbl-{name}"
    mock_gmail.list_messages_for_date.return_value = ["msg-1"]
    mock_gmail.get_message_content.return_value = {"id": "msg-1", "snippet": "Test"}

    mock_classifier = MagicMock()
    mock_classifier.filter_candidate_labels.return_value = ["Work"]
    mock_classifier.classify_sync.return_value = ClassificationResult(
        label="Work", confidence=0.95, reason="Clear work topic"
    )

    mock_notifier = MagicMock()

    processed_count = run_pipeline(
        target_date="2026-09-16",
        dry_run=True,
        limit=None,
        settings=settings,
        gmail=mock_gmail,
        classifier=mock_classifier,
        notifier=mock_notifier,
    )

    assert processed_count == 1
    # apply_label should NOT be called in dry-run mode
    mock_gmail.apply_label.assert_not_called()
    mock_notifier.send_daily_summary_sync.assert_called_once()
    assert mock_notifier.send_daily_summary_sync.call_args.kwargs["dry_run"] is True


def test_run_pipeline_with_limit(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
    settings = Settings()

    mock_gmail = MagicMock()
    mock_gmail.get_user_labels.return_value = {"Work": "lbl-work"}
    mock_gmail.ensure_label_exists.side_effect = lambda name: f"lbl-{name}"
    mock_gmail.list_messages_for_date.return_value = ["msg-1", "msg-2", "msg-3", "msg-4"]
    mock_gmail.get_message_content.return_value = {"id": "msg-x", "snippet": "Sample"}

    mock_classifier = MagicMock()
    mock_classifier.filter_candidate_labels.return_value = ["Work"]
    mock_classifier.classify_sync.return_value = ClassificationResult(
        label="Work", confidence=0.9, reason="Work"
    )

    mock_notifier = MagicMock()

    processed_count = run_pipeline(
        target_date="2026-09-16",
        dry_run=False,
        limit=2,
        settings=settings,
        gmail=mock_gmail,
        classifier=mock_classifier,
        notifier=mock_notifier,
    )

    assert processed_count == 2
    assert mock_gmail.apply_label.call_count == 2


def test_run_pipeline_handles_message_fetch_error(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
    settings = Settings()

    mock_gmail = MagicMock()
    mock_gmail.get_user_labels.return_value = {"Work": "lbl-work"}
    mock_gmail.ensure_label_exists.side_effect = lambda name: f"lbl-{name}"
    mock_gmail.list_messages_for_date.return_value = ["msg-failing", "msg-success"]

    def get_content_side_effect(msg_id):
        if msg_id == "msg-failing":
            raise RuntimeError("Transient Google API error")
        return {"id": msg_id, "snippet": "Success content"}

    mock_gmail.get_message_content.side_effect = get_content_side_effect

    mock_classifier = MagicMock()
    mock_classifier.filter_candidate_labels.return_value = ["Work"]
    mock_classifier.classify_sync.return_value = ClassificationResult(
        label="Work", confidence=0.95, reason="Work email"
    )

    mock_notifier = MagicMock()

    processed_count = run_pipeline(
        target_date="2026-09-16",
        dry_run=False,
        limit=None,
        settings=settings,
        gmail=mock_gmail,
        classifier=mock_classifier,
        notifier=mock_notifier,
    )

    assert processed_count == 2
    # Only msg-success should have apply_label called
    assert mock_gmail.apply_label.call_count == 1
    # Notifier should still be called with quarantine item recorded for failure
    mock_notifier.send_daily_summary_sync.assert_called_once()
    call_kwargs = mock_notifier.send_daily_summary_sync.call_args.kwargs
    assert len(call_kwargs["quarantined_items"]) == 1
    assert "Transient Google API error" in call_kwargs["quarantined_items"][0]["reason"]


def test_run_pipeline_concurrent(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
    settings = Settings()

    mock_gmail = MagicMock()
    mock_gmail.get_user_labels.return_value = {
        "Work": "lbl-work",
        "Personal": "lbl-personal",
        "ai-processed": "lbl-proc",
        "ai-review": "lbl-rev",
    }
    mock_gmail.ensure_label_exists.side_effect = lambda name: f"lbl-{name}"
    mock_gmail.list_messages_for_date.return_value = ["msg-1", "msg-2", "msg-3", "msg-4"]
    mock_gmail.get_message_content.side_effect = lambda mid: {"id": mid, "snippet": "Text"}

    mock_classifier = MagicMock()
    mock_classifier.filter_candidate_labels.return_value = ["Personal", "Work"]
    mock_classifier.classify_sync.return_value = ClassificationResult(
        label="Work", confidence=0.95, reason="Work email"
    )

    mock_notifier = MagicMock()

    processed_count = run_pipeline(
        target_date="2026-09-16",
        dry_run=False,
        limit=None,
        settings=settings,
        gmail=mock_gmail,
        classifier=mock_classifier,
        notifier=mock_notifier,
        concurrency=2,
    )

    assert processed_count == 4
    assert mock_gmail.apply_label.call_count == 4
    mock_notifier.send_daily_summary_sync.assert_called_once()
    call_kwargs = mock_notifier.send_daily_summary_sync.call_args.kwargs
    assert call_kwargs["total_count"] == 4
    assert call_kwargs["label_counts"] == {"Work": 4}
