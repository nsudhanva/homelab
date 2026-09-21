from gmail_classifier.config import Settings


def test_settings_custom_values(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "test-refresh-token")
    monkeypatch.setenv("LLM_BASE_URL", "http://test-llm:8080/v1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-tg-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345678")
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.85")
    monkeypatch.setenv("QUARANTINE_LABEL", "custom-review")
    monkeypatch.setenv("PROCESSED_LABEL", "custom-processed")

    settings = Settings()
    assert settings.gmail_client_id == "test-client-id"
    assert settings.gmail_client_secret == "test-client-secret"
    assert settings.gmail_refresh_token == "test-refresh-token"
    assert settings.llm_base_url == "http://test-llm:8080/v1"
    assert settings.telegram_bot_token == "test-tg-token"
    assert settings.telegram_chat_id == 12345678
    assert settings.confidence_threshold == 0.85
    assert settings.quarantine_label == "custom-review"
    assert settings.processed_label == "custom-processed"


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("CONFIDENCE_THRESHOLD", raising=False)
    monkeypatch.delenv("QUARANTINE_LABEL", raising=False)
    monkeypatch.delenv("PROCESSED_LABEL", raising=False)

    settings = Settings()
    assert settings.llm_base_url == "http://llama-server.llama.svc.cluster.local:8080/v1"
    assert settings.telegram_bot_token is None
    assert settings.telegram_chat_id == 7341944813
    assert settings.confidence_threshold == 0.80
    assert settings.quarantine_label == "ai-review"
    assert settings.processed_label == "ai-processed"
    assert settings.llm_model == "gemma-4-e2b-it"
    assert settings.archive_older_than_days == 90
    assert settings.auto_archive_enabled is True
    assert settings.account_name == "primary"
    assert settings.telegram_topic_id is None
    assert settings.allow_label_creation is True


def test_settings_archive_custom_values(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
    monkeypatch.setenv("ARCHIVE_OLDER_THAN_DAYS", "60")
    monkeypatch.setenv("AUTO_ARCHIVE_ENABLED", "false")

    settings = Settings()
    assert settings.archive_older_than_days == 60
    assert settings.auto_archive_enabled is False


def test_settings_account_and_topic_custom_values(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
    monkeypatch.setenv("ACCOUNT_NAME", "family")
    monkeypatch.setenv("TELEGRAM_TOPIC_ID", "101")

    settings = Settings()
    assert settings.account_name == "family"
    assert settings.telegram_topic_id == 101
