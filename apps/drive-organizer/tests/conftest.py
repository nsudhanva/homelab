from collections.abc import Callable
from typing import Any

import pytest
from homelab_ai import AISettings, AITask
from pydantic import BaseModel
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel


class Down(TestModel):
    """A model whose endpoint is unreachable."""

    async def request(self, *args: Any, **kwargs: Any) -> Any:
        raise ModelAPIError(model_name="local", message="Connection refused")


def returning(output: BaseModel) -> TestModel:
    return TestModel(custom_output_args=output.model_dump())


@pytest.fixture
def make_task() -> Callable[..., AITask[Any]]:
    def factory(output_type: type[Any], *models: Model) -> AITask[Any]:
        return AITask(
            name="test",
            output_type=output_type,
            instructions="test",
            settings=AISettings(_env_file=None, AI_ATTEMPTS=1),
            models=list(models),
        )

    return factory
