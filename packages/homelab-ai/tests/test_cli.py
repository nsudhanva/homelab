from typing import Any

import pytest
from pydantic_ai.models.test import TestModel

from homelab_ai import cli


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_MODEL", "local:gemma")
    monkeypatch.setenv("AI_FALLBACK_MODELS", "anthropic:claude-haiku-5-5")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_models_reports_credentials(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["models"]) == 0
    out = capsys.readouterr().out
    assert "primary   local:gemma" in out
    assert "anthropic:claude-haiku-5-5" in out
    assert "no credentials" in out


def test_ping_reports_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_build(spec: Any, *args: Any, **kwargs: Any) -> TestModel:
        return TestModel(custom_output_args={"answer": "pong"})

    monkeypatch.setattr(cli, "build_model", fake_build)
    assert cli.main(["ping", "-m", "local:gemma"]) == 0
    assert "ok    local:gemma" in capsys.readouterr().out


def test_ping_fails_without_credentials(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["ping", "-m", "anthropic:claude-haiku-5-5"]) == 1
    assert "FAIL  anthropic:claude-haiku-5-5" in capsys.readouterr().out
