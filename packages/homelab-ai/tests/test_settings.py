import pytest

from homelab_ai import AISettings, LLMConfigurationError, ModelSpec


def test_spec_parses_provider_and_keeps_colons_in_model_name() -> None:
    spec = ModelSpec.parse("OpenRouter:google/gemma-4-31b-it:free")
    assert spec == ModelSpec("openrouter", "google/gemma-4-31b-it:free")
    assert str(spec) == "openrouter:google/gemma-4-31b-it:free"


@pytest.mark.parametrize("value", ["gemma", ":gemma", "local:", ""])
def test_spec_rejects_malformed_values(value: str) -> None:
    with pytest.raises(LLMConfigurationError):
        ModelSpec.parse(value)


def test_defaults_are_haiku_first_with_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("AI_MODEL", "AI_FALLBACK_MODELS"):
        monkeypatch.delenv(var, raising=False)
    settings = AISettings(_env_file=None)
    assert [str(s) for s in settings.chain] == [
        "anthropic:claude-haiku-5-5",
        "openrouter:google/gemma-4-31b-it",
        "local:gemma-4-e2b-it",
    ]


def test_env_overrides_chain_and_dedupes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_MODEL", "anthropic:claude-haiku-5-5")
    monkeypatch.setenv("AI_FALLBACK_MODELS", "local:gemma, anthropic:claude-haiku-5-5")
    settings = AISettings(_env_file=None)
    assert [str(s) for s in settings.chain] == ["anthropic:claude-haiku-5-5", "local:gemma"]


@pytest.mark.parametrize("value", ["", "none", "NONE"])
def test_fallbacks_can_be_disabled(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("AI_FALLBACK_MODELS", value)
    assert AISettings(_env_file=None).fallback_models == []


def test_secrets_are_not_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-secret")
    assert "sk-test-secret" not in repr(AISettings(_env_file=None))
