import threading
from typing import Any

import pytest
from pydantic import BaseModel
from pydantic_ai.exceptions import FallbackExceptionGroup, ModelAPIError, ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from homelab_ai import AISettings, AITask, LLMConnectionError, LLMOutputError, is_transient


class Answer(BaseModel):
    label: str
    confidence: float


def fast_settings(**kwargs: Any) -> AISettings:
    return AISettings(_env_file=None, AI_RETRY_BACKOFF_SECONDS=0, **kwargs)


class Down(TestModel):
    def __init__(self, error: Exception | None = None) -> None:
        super().__init__()
        self.error = error or ModelAPIError(model_name="down", message="connection refused")
        self.calls = 0

    async def request(self, *args: Any, **kwargs: Any) -> Any:
        self.calls += 1
        raise self.error


def ok(label: str = "Finance") -> TestModel:
    return TestModel(custom_output_args={"label": label, "confidence": 0.9})


def task(*models: Any, **settings: Any) -> AITask[Answer]:
    return AITask(
        name="test",
        output_type=Answer,
        instructions="classify",
        settings=fast_settings(**settings),
        models=list(models),
    )


def test_returns_validated_output() -> None:
    assert task(ok()).run_sync("hi") == Answer(label="Finance", confidence=0.9)


async def test_async_run() -> None:
    assert (await task(ok("Travel")).run("hi")).label == "Travel"


def test_falls_back_to_next_model() -> None:
    primary = Down()
    assert task(primary, ok("Fallback")).run_sync("hi").label == "Fallback"
    assert primary.calls == 1


def test_retries_transient_failures_then_raises_connection_error() -> None:
    primary = Down()
    with pytest.raises(LLMConnectionError, match="connection refused"):
        task(primary, AI_ATTEMPTS=3).run_sync("hi")
    assert primary.calls == 3


def test_output_errors_are_not_retried() -> None:
    def garbage(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart("not json")])

    with pytest.raises(LLMOutputError):
        task(FunctionModel(garbage), AI_ATTEMPTS=3).run_sync("hi")


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (ModelHTTPError(status_code=503, model_name="m"), True),
        (ModelHTTPError(status_code=429, model_name="m"), True),
        (ModelHTTPError(status_code=400, model_name="m"), False),
        (ModelAPIError(model_name="m", message="reset"), True),
        (TimeoutError(), True),
        (ValueError(), False),
        (
            FallbackExceptionGroup(
                "all", [ModelAPIError(model_name="a", message="x"), TimeoutError()]
            ),
            True,
        ),
        (
            FallbackExceptionGroup(
                "mixed",
                [ModelAPIError(model_name="a", message="x"), ModelHTTPError(400, "b")],
            ),
            False,
        ),
    ],
)
def test_is_transient(exc: BaseException, expected: bool) -> None:
    assert is_transient(exc) is expected


def test_agent_is_cached_per_thread() -> None:
    t = task(ok())
    agents: list[object] = []
    worker = threading.Thread(target=lambda: agents.append(t.agent))
    worker.start()
    worker.join()
    assert t.agent is t.agent
    assert agents[0] is not t.agent


def test_describe_lists_chain() -> None:
    assert task(ok(), ok()).describe() == "test -> test"
    settings_task = AITask(
        name="x",
        output_type=Answer,
        instructions="",
        settings=fast_settings(AI_MODEL="local:gemma", AI_FALLBACK_MODELS="anthropic:c"),
    )
    assert settings_task.describe() == "local:gemma"


def test_model_settings_only_include_overrides() -> None:
    assert task(ok()).agent.model_settings is None
    assert task(ok(), AI_TEMPERATURE=0.1).agent.model_settings == {"temperature": 0.1}
