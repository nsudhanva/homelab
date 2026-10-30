from typing import Any

import pytest
from pydantic import SecretStr
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.models.test import TestModel

from homelab_ai import (
    AISettings,
    LLMConfigurationError,
    ModelSpec,
    Provider,
    build_model,
    build_routed_model,
    register_provider,
)
from homelab_ai.providers import PROVIDERS


def settings(**kwargs: Any) -> AISettings:
    base: dict[str, Any] = {
        "AI_MODEL": "local:gemma-4-e2b-it",
        "AI_FALLBACK_MODELS": "",
        "OPENROUTER_API_KEY": None,
        "ANTHROPIC_API_KEY": None,
        "OPENAI_API_KEY": None,
    }
    return AISettings(_env_file=None, **{**base, **kwargs})


def test_local_model_targets_configured_base_url() -> None:
    model = build_model(
        ModelSpec.parse("local:gemma"), settings(LOCAL_LLM_BASE_URL="http://llm:8080/v1/")
    )
    assert isinstance(model, OpenAIChatModel)
    assert model.model_name == "gemma"
    assert model.base_url.rstrip("/") == "http://llm:8080/v1"


def test_anthropic_sends_workspace_header() -> None:
    model = build_model(
        ModelSpec.parse("anthropic:claude-haiku-5-5"),
        settings(ANTHROPIC_API_KEY=SecretStr("k"), ANTHROPIC_WORKSPACE_ID="wrkspc_1"),
    )
    assert isinstance(model, AnthropicModel)
    client = model.client
    assert client._custom_headers["anthropic-workspace-id"] == "wrkspc_1"


def test_openrouter_and_openai_build_when_keys_present() -> None:
    s = settings(OPENROUTER_API_KEY=SecretStr("k"), OPENAI_API_KEY=SecretStr("k"))
    assert isinstance(build_model(ModelSpec.parse("openrouter:google/gemma"), s), OpenRouterModel)
    assert isinstance(build_model(ModelSpec.parse("openai:gpt-5"), s), OpenAIChatModel)


def test_build_model_requires_credentials() -> None:
    with pytest.raises(LLMConfigurationError, match="no credentials"):
        build_model(ModelSpec.parse("anthropic:claude-haiku-5-5"), settings())


def test_unknown_provider_lists_known_ones() -> None:
    with pytest.raises(LLMConfigurationError, match="Known providers"):
        build_model(ModelSpec.parse("nope:model"), settings())


def test_routed_model_skips_providers_without_credentials() -> None:
    s = settings(AI_FALLBACK_MODELS="openrouter:x,anthropic:claude-haiku-5-5")
    assert isinstance(build_routed_model(s), OpenAIChatModel)


def test_routed_model_chains_usable_models() -> None:
    s = settings(AI_FALLBACK_MODELS="anthropic:claude-haiku-5-5", ANTHROPIC_API_KEY=SecretStr("k"))
    model = build_routed_model(s)
    assert isinstance(model, FallbackModel)
    assert [m.model_name for m in model.models] == ["gemma-4-e2b-it", "claude-haiku-5-5"]


def test_routed_model_fails_when_nothing_is_usable() -> None:
    with pytest.raises(LLMConfigurationError, match="No usable models"):
        build_routed_model(settings(AI_MODEL="anthropic:claude-haiku-5-5"))


def test_register_provider_extends_specs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(PROVIDERS, "fake", PROVIDERS["local"])
    register_provider("Fake", Provider(build=lambda ctx: TestModel(model_name=ctx.spec.name)))
    assert build_model(ModelSpec.parse("fake:m1"), settings()).model_name == "m1"


def test_timeout_and_retry_overrides_reach_client() -> None:
    model = build_model(
        ModelSpec.parse("local:gemma"), settings(AI_TIMEOUT_SECONDS=7, AI_MAX_RETRIES=3)
    )
    assert isinstance(model, OpenAIChatModel)
    assert model.client.timeout == 7
    assert model.client.max_retries == 3
