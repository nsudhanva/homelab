"""Unit tests for ModelRouter high-availability routing and agent creation."""

from typing import Any

from pydantic import BaseModel
from pydantic_ai.exceptions import FallbackExceptionGroup, ModelAPIError
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.models.test import TestModel

from homelab_ai.config import LLMClientConfig
from homelab_ai.providers import CustomModelProviderBuilder
from homelab_ai.router import ModelRouter


class SampleOutput(BaseModel):
    summary: str
    confidence: float


def test_build_primary_local_model() -> None:
    config = LLMClientConfig(primary_provider="local")
    router = ModelRouter(config)
    model = router.build_primary_model()
    assert isinstance(model, OpenAIChatModel)
    assert model.model_name == "gemma-4-e2b-it"


def test_build_primary_openrouter_model() -> None:
    config = LLMClientConfig(
        primary_provider="openrouter",
        openrouter_api_key="test-key",
    )
    router = ModelRouter(config)
    model = router.build_primary_model()
    assert isinstance(model, OpenRouterModel)
    assert model.model_name == "google/gemma-4-31b-it"


def test_build_routed_model_with_fallback() -> None:
    config = LLMClientConfig(
        primary_provider="local",
        fallback_provider="openrouter",
        openrouter_api_key="test-key",
    )
    router = ModelRouter(config)
    routed = router.build_routed_model()
    assert isinstance(routed, FallbackModel)


def test_build_routed_model_without_openrouter_key() -> None:
    config = LLMClientConfig(
        primary_provider="local",
        fallback_provider="openrouter",
        openrouter_api_key="",
    )
    router = ModelRouter(config)
    routed = router.build_routed_model()
    assert isinstance(routed, OpenAIChatModel)
    assert not isinstance(routed, FallbackModel)


def test_build_routed_model_fallback_none() -> None:
    config = LLMClientConfig(
        primary_provider="local",
        fallback_provider="none",
    )
    router = ModelRouter(config)
    routed = router.build_routed_model()
    assert isinstance(routed, OpenAIChatModel)
    assert not isinstance(routed, FallbackModel)


def test_build_routed_model_flipped_openrouter_primary() -> None:
    config = LLMClientConfig(
        primary_provider="openrouter",
        fallback_provider="local",
        openrouter_api_key="test-key",
    )
    router = ModelRouter(config)
    routed = router.build_routed_model()
    assert isinstance(routed, FallbackModel)


def test_create_agent_with_custom_models() -> None:
    primary = TestModel(custom_output_args={"summary": "from primary", "confidence": 0.95})
    fallback = TestModel(custom_output_args={"summary": "from fallback", "confidence": 0.85})

    router = ModelRouter(
        custom_primary_builder=CustomModelProviderBuilder(primary),
        custom_fallback_builder=CustomModelProviderBuilder(fallback),
    )
    agent = router.create_agent(output_type=SampleOutput, system_prompt="Test system prompt")

    res = agent.run_sync("Hello")
    assert res.output.summary == "from primary"
    assert res.output.confidence == 0.95


def test_agent_fallback_execution_on_failure() -> None:
    class FailingModel(TestModel):
        async def request(self, *args: Any, **kwargs: Any) -> Any:
            raise ModelAPIError(model_name="gemma-4-e2b-it", message="Connection Refused 502")

    fallback = TestModel(custom_output_args={"summary": "rescued by fallback", "confidence": 0.99})

    router = ModelRouter(
        custom_primary_builder=CustomModelProviderBuilder(FailingModel()),
        custom_fallback_builder=CustomModelProviderBuilder(fallback),
    )
    agent = router.create_agent(output_type=SampleOutput)

    res = agent.run_sync("Classify this")
    assert res.output.summary == "rescued by fallback"
    assert res.output.confidence == 0.99


def test_unwrap_fallback_error() -> None:
    err1 = ModelAPIError(model_name="m1", message="Primary failed")
    err2 = ModelAPIError(model_name="m2", message="Fallback failed")
    group = FallbackExceptionGroup("Both failed", [err1, err2])

    unwrapped = ModelRouter.unwrap_fallback_error(group)
    assert len(unwrapped) == 2
    assert unwrapped[0] is err1
    assert unwrapped[1] is err2

    single = RuntimeError("Simple error")
    assert ModelRouter.unwrap_fallback_error(single) == [single]
