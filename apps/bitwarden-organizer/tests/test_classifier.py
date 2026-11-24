from typing import Any

import pytest
from homelab_ai import AISettings, AITask, LLMConnectionError
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel

from bitwarden_organizer.classifier import INSTRUCTIONS, FolderChoice, FolderClassifier
from bitwarden_organizer.items import summarize

from .conftest import FOLDERS, login_item

ITEM = summarize(login_item("1", "costco.com", "https://costco.com"))


class Down(TestModel):
    async def request(self, *args: Any, **kwargs: Any) -> Any:
        raise ModelAPIError(model_name="local", message="connection refused")


def answer(folder: str, confidence: float = 0.95) -> TestModel:
    return TestModel(
        custom_output_args={"folder": folder, "confidence": confidence, "reason": "Store"}
    )


def classifier_with(*models: Model) -> FolderClassifier:
    task = AITask(
        name="bitwarden-organizer",
        output_type=FolderChoice,
        instructions=INSTRUCTIONS,
        settings=AISettings(_env_file=None, AI_ATTEMPTS=1),
        models=list(models),
    )
    return FolderClassifier(task=task)


def test_returns_matching_folder_ignoring_case() -> None:
    decision = classifier_with(answer(" shopping ")).classify(ITEM, FOLDERS, "guide")
    assert decision is not None
    assert decision.folder.id == "f-shop"
    assert decision.confidence == 0.95


def test_keeps_low_confidence_choice() -> None:
    decision = classifier_with(answer("Finance", 0.4)).classify(ITEM, FOLDERS, "guide")
    assert decision is not None
    assert decision.folder.name == "Finance"


def test_unknown_folder_returns_none() -> None:
    assert classifier_with(answer("Groceries")).classify(ITEM, FOLDERS, "guide") is None


def test_connection_error_propagates() -> None:
    with pytest.raises(LLMConnectionError):
        classifier_with(Down()).classify(ITEM, FOLDERS, "guide")
