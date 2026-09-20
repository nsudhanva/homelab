"""Tests for Pydantic AI FallbackModel routing in DriveClassifier.

Validates that when the local LLM endpoint (llama-server) crashes or is unreachable,
FallbackModel automatically and seamlessly routes classification and folder triage
requests to OpenRouter Gemma 4 31B without downtime or unhandled errors.
Also validates provider flipping, configuration parsing, graceful degradation when API keys
are absent, and pre-router deterministic handling when both endpoints fail.
"""

from unittest.mock import patch

import pytest
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from drive_organizer.classifier import (
    DocumentClassification,
    DriveClassifier,
    FolderTriageDecision,
    LLMConnectionError,
)
from drive_organizer.config import Settings


def test_settings_llm_provider_configuration_parsing(monkeypatch):
    """Verify that Settings parses all LLM provider routing and timeout configuration."""
    # Test defaults
    settings = Settings()
    assert settings.primary_llm_provider == "local"
    assert settings.fallback_llm_provider == "openrouter"
    assert settings.llm_timeout_seconds == 120.0
    assert settings.openrouter_api_key == ""
    assert settings.openrouter_base_url == "https://openrouter.ai/api/v1"
    assert settings.openrouter_model_name == "google/gemma-4-31b-it"

    # Test environment variable overrides
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("FALLBACK_LLM_PROVIDER", "local")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "45.5")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-testkey123")
    monkeypatch.setenv("OPENROUTER_MODEL_NAME", "anthropic/claude-3-haiku")

    custom_settings = Settings()
    assert custom_settings.primary_llm_provider == "openrouter"
    assert custom_settings.fallback_llm_provider == "local"
    assert custom_settings.llm_timeout_seconds == 45.5
    assert custom_settings.openrouter_api_key == "sk-or-v1-testkey123"
    assert custom_settings.openrouter_model_name == "anthropic/claude-3-haiku"


def test_missing_openrouter_api_key_gracefully_degrades_at_startup():
    """Verify missing OPENROUTER_API_KEY with primary=local degrades to single local model without error."""
    classifier = DriveClassifier(
        primary_llm_provider="local",
        fallback_llm_provider="openrouter",
        openrouter_api_key="",
    )
    model = classifier._build_model()
    # Should be a single OpenAIChatModel, not a FallbackModel
    assert isinstance(model, OpenAIChatModel)
    assert not isinstance(model, FallbackModel)


def test_missing_openrouter_api_key_when_primary_is_openrouter_falls_back_to_local(caplog):
    """Verify that if primary is openrouter but OPENROUTER_API_KEY is missing, it logs warning and uses local."""
    classifier = DriveClassifier(
        primary_llm_provider="openrouter",
        fallback_llm_provider="local",
        openrouter_api_key="",
    )
    with caplog.at_level("WARNING"):
        model = classifier._build_model()
    assert isinstance(model, OpenAIChatModel)
    assert not isinstance(model, FallbackModel)
    assert "Primary provider is openrouter but OPENROUTER_API_KEY is not set" in caplog.text


def test_fallback_disabled_when_provider_is_none():
    """Verify that when FALLBACK_LLM_PROVIDER=none, no FallbackModel is constructed even if key is present."""
    classifier = DriveClassifier(
        primary_llm_provider="local",
        fallback_llm_provider="none",
        openrouter_api_key="sk-or-dummy-key",
    )
    model = classifier._build_model()
    assert isinstance(model, OpenAIChatModel)
    assert not isinstance(model, FallbackModel)


def test_fallback_model_routes_document_classification_when_local_endpoint_unreachable():
    """Verify that when local LLM endpoint is crashed/unreachable, FallbackModel routes to OpenRouter."""
    openrouter_output = {
        "person": "Sudhanva",
        "jurisdiction": "USA",
        "category": "Career",
        "subcategory": "Interview Prep",
        "clean_filename": "System Design Cheatsheet.pdf",
        "is_joint": False,
        "confidence": 0.96,
        "summary": "Distributed systems notes routed via OpenRouter Gemma 4 31B",
        "search_tags": ["system design", "interview", "distributed systems"],
        "reasoning": "Fallback routing to OpenRouter Gemma 4 31B succeeded after local endpoint failure",
    }
    openrouter_model = TestModel(
        custom_output_args=openrouter_output,
        model_name="google/gemma-4-31b-it",
    )

    classifier = DriveClassifier(
        base_url="http://127.0.0.1:9999/v1",
        timeout_seconds=0.2,
        fallback_model=openrouter_model,
    )

    res = classifier.classify_sync(
        filename="System Design Cheatsheet.pdf",
        extracted_text="Consistent hashing, Raft consensus, vector clocks, gossip protocol",
        mime_type="application/pdf",
    )

    assert isinstance(res, DocumentClassification)
    assert res.person == "Sudhanva"
    assert res.category == "Career"
    assert res.subcategory == "Interview Prep"
    assert res.clean_filename == "System Design Cheatsheet.pdf"
    assert "OpenRouter Gemma 4 31B" in res.summary
    assert res.confidence == 0.96


def test_fallback_model_routes_folder_triage_when_local_endpoint_unreachable():
    """Verify that folder triage seamlessly fails over to OpenRouter Gemma 4 31B when local LLM is down."""
    triage_output = {
        "action": "keep_intact",
        "is_code": True,
        "target_folder": "Code/homelab-repo",
        "confidence": 0.98,
        "reasoning": "Software repository containing infrastructure manifests and scripts.",
    }
    openrouter_triage_model = TestModel(
        custom_output_args=triage_output,
        model_name="google/gemma-4-31b-it",
    )

    classifier = DriveClassifier(
        base_url="http://127.0.0.1:9999/v1",
        timeout_seconds=0.2,
        fallback_triage_model=openrouter_triage_model,
    )

    decision = classifier.triage_folder_sync(
        folder_name="homelab-repo",
        sample_files=["package.json", "src/main.ts", "Dockerfile"],
        tree_summary="homelab-repo/\n  src/main.ts\n  Dockerfile",
    )

    assert isinstance(decision, FolderTriageDecision)
    assert decision.action == "keep_intact"
    assert decision.is_code is True
    assert decision.target_folder == "Code/homelab-repo"
    assert decision.confidence == 0.98


def test_healthy_local_model_does_not_trigger_fallback():
    """Verify that when local LLM endpoint is healthy, fallback model is not invoked."""
    healthy_output = {
        "person": "Sudhanva",
        "jurisdiction": "USA",
        "category": "Identity",
        "clean_filename": "Passport.pdf",
        "is_joint": False,
        "confidence": 0.95,
        "summary": "Classified by local llama-server",
        "search_tags": ["passport"],
        "reasoning": "Local model processed successfully",
    }
    local_model = TestModel(custom_output_args=healthy_output, model_name="gemma-4-e2b-it")

    class SpyFallbackModel(TestModel):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.calls = 0

        async def request(self, *args, **kwargs):
            self.calls += 1
            return await super().request(*args, **kwargs)

    fallback_model = SpyFallbackModel(
        custom_output_args=healthy_output,
        model_name="google/gemma-4-31b-it",
    )

    fb = FallbackModel(local_model, fallback_model)
    agent = Agent(model=fb, output_type=DocumentClassification)
    res = agent.run_sync("Classify document")

    assert res.output.summary == "Classified by local llama-server"
    assert fallback_model.calls == 0


def test_provider_flip_routes_to_openrouter_first():
    """Verify that when PRIMARY_LLM_PROVIDER=openrouter, OpenRouter is called first and local is untouched."""
    or_output = {
        "person": "Sudhanva",
        "jurisdiction": "USA",
        "category": "Career",
        "clean_filename": "Offer Letter.pdf",
        "is_joint": False,
        "confidence": 0.99,
        "summary": "Classified via Primary OpenRouter",
        "search_tags": ["career"],
        "reasoning": "Primary OpenRouter responded",
    }

    class SpyModel(TestModel):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.calls = 0

        async def request(self, *args, **kwargs):
            self.calls += 1
            return await super().request(*args, **kwargs)

    openrouter_primary = SpyModel(custom_output_args=or_output, model_name="google/gemma-4-31b-it")
    local_fallback = SpyModel(custom_output_args=or_output, model_name="gemma-4-e2b-it")

    classifier = DriveClassifier(
        primary_llm_provider="openrouter",
        fallback_llm_provider="local",
        primary_model=openrouter_primary,
        fallback_model=local_fallback,
    )

    res = classifier.classify_sync(
        filename="Offer Letter.pdf",
        extracted_text="Employment offer details",
        mime_type="application/pdf",
    )

    assert res.summary == "Classified via Primary OpenRouter"
    assert openrouter_primary.calls == 1
    assert local_fallback.calls == 0


def test_provider_flip_openrouter_fails_falls_back_to_local():
    """Verify that when PRIMARY_LLM_PROVIDER=openrouter and OpenRouter fails, it falls back to local."""

    class FailingOpenRouterModel(TestModel):
        async def request(self, *args, **kwargs):
            raise ModelAPIError(
                model_name="google/gemma-4-31b-it", message="OpenRouter 503 Overloaded"
            )

    local_output = {
        "person": "Sudhanva",
        "jurisdiction": "USA",
        "category": "Identity",
        "clean_filename": "Passport.pdf",
        "is_joint": False,
        "confidence": 0.93,
        "summary": "Classified by local fallback after OpenRouter 503",
        "search_tags": ["passport"],
        "reasoning": "Local model fallback executed",
    }
    local_fallback = TestModel(custom_output_args=local_output, model_name="gemma-4-e2b-it")

    classifier = DriveClassifier(
        primary_llm_provider="openrouter",
        fallback_llm_provider="local",
        primary_model=FailingOpenRouterModel(),
        fallback_model=local_fallback,
    )

    res = classifier.classify_sync(
        filename="Passport.pdf",
        extracted_text="United States Passport details",
        mime_type="application/pdf",
    )

    assert res.summary == "Classified by local fallback after OpenRouter 503"
    assert res.confidence == 0.93


def test_both_models_fail_triggers_preroute_fallback():
    """Verify that when both primary and fallback models fail, confident pre-router heuristics handle it."""

    class AlwaysFailingModel(TestModel):
        async def request(self, *args, **kwargs):
            raise ModelAPIError(model_name="test-model", message="Connection refused")

    classifier = DriveClassifier(
        primary_model=AlwaysFailingModel(),
        fallback_model=AlwaysFailingModel(),
    )

    with patch("time.sleep", return_value=None):
        res = classifier.classify_sync(
            filename="checkpoint.safetensors",
            extracted_text="",
            mime_type="application/octet-stream",
        )

    # PreRouter classifies .safetensors as Models with >= 0.90 confidence
    assert res.category == "Models"
    assert "LLM unreachable; pre-routing fallback" in res.reasoning


def test_both_models_fail_unidentifiable_file_raises_connection_error():
    """Verify that when both models fail and pre-router cannot identify, LLMConnectionError is raised."""

    class AlwaysFailingModel(TestModel):
        async def request(self, *args, **kwargs):
            raise ModelAPIError(model_name="test-model", message="Connection refused")

    classifier = DriveClassifier(
        primary_model=AlwaysFailingModel(),
        fallback_model=AlwaysFailingModel(),
    )

    with patch("time.sleep", return_value=None):
        with pytest.raises(LLMConnectionError) as exc_info:
            classifier.classify_sync(
                filename="unidentifiable_random_junk_file.xyz",
                extracted_text="",
                mime_type="application/octet-stream",
            )
        assert "LLM classification failed" in str(exc_info.value)
        assert "All models from FallbackModel failed" in str(exc_info.value)


def test_pydantic_ai_openrouter_provider_and_model_behavior():
    """Verify that OpenRouterProvider and OpenRouterModel instantiate and integrate correctly in Pydantic AI."""
    provider = OpenRouterProvider(
        api_key="sk-or-test-key",
        app_url="https://github.com/nsudhanva/homelab",
        app_title="homelab-drive-organizer",
    )
    assert provider.name == "openrouter"
    model = OpenRouterModel("google/gemma-4-31b-it", provider=provider)
    assert model.model_name == "google/gemma-4-31b-it"

    # Verify FallbackModel accepts OpenRouterModel
    fb = FallbackModel(model, "test")
    assert len(fb.models) == 2
