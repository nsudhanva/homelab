"""Unit tests for homelab-ai configuration schema."""

import pytest
from pydantic import ValidationError

from homelab_ai.config import LLMClientConfig


def test_default_config() -> None:
    config = LLMClientConfig()
    assert config.primary_provider == "local"
    assert config.fallback_provider == "openrouter"
    assert config.llm_base_url == "http://llama-server.llama.svc.cluster.local:8080/v1"
    assert config.llm_model_name == "gemma-4-e2b-it"
    assert config.llm_timeout_seconds == 120.0
    assert config.openrouter_base_url == "https://openrouter.ai/api/v1"
    assert config.openrouter_model_name == "google/gemma-4-31b-it"
    assert config.openrouter_api_key == ""
    assert config.app_name == "homelab-ai"


def test_custom_config() -> None:
    config = LLMClientConfig(
        primary_provider="openrouter",
        fallback_provider="local",
        llm_timeout_seconds=45.0,
        openrouter_api_key="sk-or-test-key",
        app_name="custom-agent",
    )
    assert config.primary_provider == "openrouter"
    assert config.fallback_provider == "local"
    assert config.llm_timeout_seconds == 45.0
    assert config.openrouter_api_key == "sk-or-test-key"
    assert config.app_name == "custom-agent"


def test_invalid_provider_fails_validation() -> None:
    with pytest.raises(ValidationError):
        LLMClientConfig.model_validate({"primary_provider": "unsupported-engine"})


def test_env_var_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("FALLBACK_LLM_PROVIDER", "local")
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-key-1234")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "30.0")

    config = LLMClientConfig()
    assert config.primary_provider == "openrouter"
    assert config.fallback_provider == "local"
    assert config.openrouter_api_key == "env-key-1234"
    assert config.llm_timeout_seconds == 30.0
