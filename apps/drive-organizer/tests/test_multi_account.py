from unittest.mock import MagicMock, patch

from drive_organizer.config import Settings
from drive_organizer.notifier import OrganizerRunStats, TelegramNotifier


def test_settings_account_name_default() -> None:
    settings = Settings()
    assert settings.account_name == "personal"
    assert settings.telegram_topic_id is None


def test_settings_account_name_env_override(monkeypatch) -> None:
    monkeypatch.setenv("ACCOUNT_NAME", "family")
    monkeypatch.setenv("TELEGRAM_TOPIC_ID", "12345")
    settings = Settings()
    assert settings.account_name == "family"
    assert settings.telegram_topic_id == 12345


def test_notifier_account_badge() -> None:
    notifier = TelegramNotifier("fake_token", "fake_chat", account_name="family")
    stats = OrganizerRunStats(total_scanned=2, total_docs_classified=2)

    with patch.object(notifier, "send_message_sync", return_value=True) as mock_send:
        notifier.send_summary(stats)
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "[Family]" in text
        assert "Google Drive Organizer Report [Family]" in text


def test_notifier_telegram_topic_id() -> None:
    notifier = TelegramNotifier("fake_token", "fake_chat", account_name="family", topic_id=999)
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_client.post.return_value = mock_resp

        success = notifier.send_message_sync("Test message")
        assert success is True
        mock_client.post.assert_called_once()
        call_json = mock_client.post.call_args[1]["json"]
        assert call_json["message_thread_id"] == 999
        assert call_json["chat_id"] == "fake_chat"
