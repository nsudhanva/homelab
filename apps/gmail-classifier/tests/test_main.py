from unittest.mock import MagicMock

import pytest

from gmail_classifier.classifier import ClassificationResult
from gmail_classifier.config import Settings
from gmail_classifier.main import (
    parse_arguments,
    run_archive_sweep,
    run_mark_all_read,
    run_pipeline,
)


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
    for name in ("AUTO_ARCHIVE_ENABLED", "ARCHIVE_OLDER_THAN_DAYS"):
        monkeypatch.delenv(name, raising=False)
    return Settings(_env_file=None, AUTO_ARCHIVE_ENABLED=True, ARCHIVE_OLDER_THAN_DAYS=90)


def test_parse_arguments():
    args = parse_arguments([])
    assert args.date is None
    assert args.days is None
    assert args.dry_run is False
    assert args.limit is None
    assert args.mark_all_read is False
    assert args.archive_only is False

    args = parse_arguments(
        [
            "--date",
            "2026-09-15",
            "--days",
            "7",
            "--inbox",
            "--dry-run",
            "--limit",
            "10",
            "--concurrency",
            "2",
            "--archive-days",
            "60",
            "--archive-only",
            "--mark-all-read",
            "--account",
            "family",
        ]
    )
    assert args.date == "2026-09-15"
    assert args.days == 7
    assert args.inbox is True
    assert args.dry_run is True
    assert args.limit == 10
    assert args.concurrency == 2
    assert args.archive_days == 60
    assert args.archive_only is True
    assert args.mark_all_read is True
    assert args.account == "family"


def test_run_pipeline_normal(settings):
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
    mock_classifier.classify.side_effect = [
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
    mock_gmail.apply_label.assert_any_call("msg-1", add_label_ids=["lbl-work", "lbl-ai-processed"])
    mock_gmail.apply_label.assert_any_call(
        "msg-2", add_label_ids=["lbl-ai-review", "lbl-ai-processed"]
    )
    mock_notifier.send_daily_summary.assert_called_once()
    call_kwargs = mock_notifier.send_daily_summary.call_args.kwargs
    assert call_kwargs["total_count"] == 2
    assert call_kwargs["label_counts"] == {"Work": 1, "ai-review": 1}
    assert len(call_kwargs["quarantined_items"]) == 1


def test_run_pipeline_dry_run(settings):
    mock_gmail = MagicMock()
    mock_gmail.get_user_labels.return_value = {"Work": "lbl-work"}
    mock_gmail.ensure_label_exists.side_effect = lambda name: f"lbl-{name}"
    mock_gmail.list_messages_for_date.return_value = ["msg-1"]
    mock_gmail.get_message_content.return_value = {"id": "msg-1", "snippet": "Test"}

    mock_classifier = MagicMock()
    mock_classifier.filter_candidate_labels.return_value = ["Work"]
    mock_classifier.classify.return_value = ClassificationResult(
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
    mock_gmail.apply_label.assert_not_called()
    mock_notifier.send_daily_summary.assert_called_once()
    assert mock_notifier.send_daily_summary.call_args.kwargs["dry_run"] is True


def test_run_pipeline_with_limit(settings):
    mock_gmail = MagicMock()
    mock_gmail.get_user_labels.return_value = {"Work": "lbl-work"}
    mock_gmail.ensure_label_exists.side_effect = lambda name: f"lbl-{name}"
    mock_gmail.list_messages_for_date.return_value = ["msg-1", "msg-2", "msg-3", "msg-4"]
    mock_gmail.get_message_content.return_value = {"id": "msg-x", "snippet": "Sample"}

    mock_classifier = MagicMock()
    mock_classifier.filter_candidate_labels.return_value = ["Work"]
    mock_classifier.classify.return_value = ClassificationResult(
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


def test_run_pipeline_handles_message_fetch_error(settings):
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
    mock_classifier.classify.return_value = ClassificationResult(
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
    assert mock_gmail.apply_label.call_count == 1
    mock_notifier.send_daily_summary.assert_called_once()
    call_kwargs = mock_notifier.send_daily_summary.call_args.kwargs
    assert len(call_kwargs["quarantined_items"]) == 1
    assert "Transient Google API error" in call_kwargs["quarantined_items"][0]["reason"]


def test_run_archive_sweep_enabled(settings):

    mock_gmail = MagicMock()
    mock_gmail.list_messages_to_archive.return_value = ["arch-1", "arch-2", "arch-3"]
    mock_gmail.batch_archive_messages.return_value = 3

    count = run_archive_sweep(settings=settings, gmail=mock_gmail, dry_run=False)
    assert count == 3
    mock_gmail.list_messages_to_archive.assert_called_once_with(
        older_than_days=90,
        quarantine_label="ai-review",
        limit=None,
    )
    mock_gmail.batch_archive_messages.assert_called_once_with(["arch-1", "arch-2", "arch-3"])

    mock_gmail.reset_mock()
    mock_gmail.list_messages_to_archive.return_value = ["arch-1", "arch-2"]
    count_dry = run_archive_sweep(settings=settings, gmail=mock_gmail, dry_run=True)
    assert count_dry == 2
    mock_gmail.batch_archive_messages.assert_not_called()


def test_run_archive_sweep_disabled(settings):
    settings.auto_archive_enabled = False

    mock_gmail = MagicMock()
    count = run_archive_sweep(settings=settings, gmail=mock_gmail)
    assert count == 0
    mock_gmail.list_messages_to_archive.assert_not_called()


def test_run_mark_all_read(settings):
    mock_gmail = MagicMock()
    mock_gmail.list_unread_messages.return_value = ["u-1", "u-2"]
    mock_gmail.batch_mark_read.return_value = 2
    assert run_mark_all_read(settings=settings, gmail=mock_gmail) == 2
    mock_gmail.batch_mark_read.assert_called_once_with(["u-1", "u-2"])

    mock_gmail.reset_mock()
    mock_gmail.list_unread_messages.return_value = ["u-1"]
    assert run_mark_all_read(settings=settings, gmail=mock_gmail, dry_run=True) == 1
    mock_gmail.batch_mark_read.assert_not_called()

    mock_gmail.reset_mock()
    mock_gmail.list_unread_messages.return_value = []
    assert run_mark_all_read(settings=settings, gmail=mock_gmail) == 0
    mock_gmail.batch_mark_read.assert_not_called()
