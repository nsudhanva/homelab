from gmail_classifier.config import Settings


def set_credentials(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "test-refresh-token")


def test_settings_read_environment(monkeypatch):
    set_credentials(monkeypatch)
    for name, value in {
        "TELEGRAM_BOT_TOKEN": "test-tg-token",
        "TELEGRAM_CHAT_ID": "12345678",
        "CONFIDENCE_THRESHOLD": "0.85",
        "QUARANTINE_LABEL": "custom-review",
        "PROCESSED_LABEL": "custom-processed",
        "ARCHIVE_OLDER_THAN_DAYS": "60",
        "AUTO_ARCHIVE_ENABLED": "false",
        "ACCOUNT_NAME": "family",
        "TELEGRAM_TOPIC_ID": "101",
    }.items():
        monkeypatch.setenv(name, value)

    settings = Settings(_env_file=None)
    assert settings.gmail_client_id == "test-client-id"
    assert settings.gmail_client_secret == "test-client-secret"
    assert settings.gmail_refresh_token == "test-refresh-token"
    assert settings.telegram_bot_token == "test-tg-token"
    assert settings.telegram_chat_id == 12345678
    assert settings.confidence_threshold == 0.85
    assert settings.quarantine_label == "custom-review"
    assert settings.processed_label == "custom-processed"
    assert settings.archive_older_than_days == 60
    assert settings.auto_archive_enabled is False
    assert settings.account_name == "family"
    assert settings.telegram_topic_id == 101


def test_settings_default_mailbox_policy(monkeypatch):
    set_credentials(monkeypatch)
    for name in (
        "CONFIDENCE_THRESHOLD",
        "QUARANTINE_LABEL",
        "PROCESSED_LABEL",
        "ARCHIVE_OLDER_THAN_DAYS",
        "AUTO_ARCHIVE_ENABLED",
        "ALLOW_LABEL_CREATION",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)
    assert settings.confidence_threshold == 0.80
    assert settings.quarantine_label == "ai-review"
    assert settings.processed_label == "ai-processed"
    assert settings.archive_older_than_days == 90
    assert settings.auto_archive_enabled is True
    assert settings.allow_label_creation is True
