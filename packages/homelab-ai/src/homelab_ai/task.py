"""AITask: one structured-output LLM call with fallback, retries, and typed errors."""

import asyncio
import logging
import os
import threading
import time
from collections.abc import Sequence
from typing import Any

from pydantic_ai import Agent, CachePoint
from pydantic_ai.exceptions import (
    AgentRunError,
    FallbackExceptionGroup,
    ModelAPIError,
    ModelHTTPError,
)
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from .exceptions import LLMConnectionError, LLMOutputError
from .providers import available_specs, build_routed_model, chain_models
from .settings import AISettings

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
logger = logging.getLogger(__name__)


def is_transient(exc: BaseException) -> bool:
    """True when the failure is infrastructure (network, timeout, 429, 5xx), not output."""
    if isinstance(exc, FallbackExceptionGroup):
        return all(is_transient(e) for e in exc.exceptions)
    if isinstance(exc, ModelHTTPError):
        return exc.status_code == 429 or exc.status_code >= 500
    return isinstance(exc, ModelAPIError | TimeoutError | ConnectionError)


def describe_failure(exc: BaseException) -> str:
    """One line per failed model, so logs show which provider broke and why."""
    if isinstance(exc, FallbackExceptionGroup):
        return "; ".join(describe_failure(e) for e in exc.exceptions)
    return f"{type(exc).__name__}: {exc}"


class AITask[OutputT]:
    """A named LLM task that returns validated ``OutputT``.

    The model chain comes from ``AISettings`` (``AI_MODEL`` and ``AI_FALLBACK_MODELS``)
    unless ``models`` is given, which tests use to inject Pydantic AI test models.
    Agents are cached per thread because provider HTTP clients bind to the event loop
    that first used them, and ``run_sync`` runs a loop per worker thread.
    """

    def __init__(
        self,
        *,
        name: str,
        output_type: type[OutputT],
        instructions: str,
        settings: AISettings | None = None,
        models: Sequence[Model] | None = None,
        output_retries: int = 2,
    ) -> None:
        self.name = name
        self.output_type = output_type
        self.instructions = instructions
        self.settings = settings or AISettings()
        self._models = list(models) if models else None
        self.output_retries = output_retries
        self._local = threading.local()

    def describe(self) -> str:
        if self._models:
            return " -> ".join(m.model_name for m in self._models)
        return " -> ".join(map(str, available_specs(self.settings))) or "no usable models"

    @property
    def agent(self) -> Agent[None, OutputT]:
        agent = getattr(self._local, "agent", None)
        if agent is None:
            model = (
                chain_models(self._models)
                if self._models
                else build_routed_model(self.settings, app_name=f"homelab-{self.name}")
            )
            agent = Agent(
                model,
                output_type=self.output_type,
                instructions=self.instructions,
                retries=self.output_retries,
                model_settings=self._model_settings(),
                name=self.name,
            )
            self._local.agent = agent
        return agent

    def _model_settings(self) -> ModelSettings | None:
        values: dict[str, Any] = {
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
            "thinking": self.settings.effort,
        }
        settings = {k: v for k, v in values.items() if v is not None}
        return ModelSettings(**settings) if settings else None

    def _handle_failure(self, exc: Exception, attempt: int) -> float:
        """Log a failed attempt; return the backoff before retrying, or raise a typed error."""
        transient = is_transient(exc)
        attempts = self.settings.attempts
        logger.warning(
            f"[{self.name}] attempt {attempt}/{attempts} failed "
            f"({'transient' if transient else 'output'}): {describe_failure(exc)}"
        )
        if transient and attempt < attempts:
            return self.settings.retry_backoff_seconds * attempt
        error = LLMConnectionError if transient else LLMOutputError
        raise error(f"[{self.name}] {describe_failure(exc)}") from exc

    @staticmethod
    def _user_prompt(prompt: str, stable_prefix: str | None) -> str | list[str | CachePoint]:
        """Put ``stable_prefix`` before a cache breakpoint so providers that cache reuse it."""
        return [stable_prefix, CachePoint(), prompt] if stable_prefix else prompt

    def run_sync(self, prompt: str, *, stable_prefix: str | None = None) -> OutputT:
        """Run the task. ``stable_prefix`` is text shared by many calls, such as a label list."""
        user_prompt = self._user_prompt(prompt, stable_prefix)
        for attempt in range(1, self.settings.attempts + 1):
            try:
                return self.agent.run_sync(user_prompt).output
            except (AgentRunError, FallbackExceptionGroup, TimeoutError, ConnectionError) as exc:
                time.sleep(self._handle_failure(exc, attempt))
        raise AssertionError("unreachable")

    async def run(self, prompt: str, *, stable_prefix: str | None = None) -> OutputT:
        user_prompt = self._user_prompt(prompt, stable_prefix)
        for attempt in range(1, self.settings.attempts + 1):
            try:
                return (await self.agent.run(user_prompt)).output
            except (AgentRunError, FallbackExceptionGroup, TimeoutError, ConnectionError) as exc:
                await asyncio.sleep(self._handle_failure(exc, attempt))
        raise AssertionError("unreachable")
