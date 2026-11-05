"""Drive-specific behavior when the model chain fails over or fails completely."""

from collections.abc import Callable
from typing import Any

import pytest
from homelab_ai import AITask
from pydantic_ai.models.test import TestModel

from drive_organizer.classifier import (
    DocumentClassification,
    DriveClassifier,
    FolderTriageDecision,
    LLMConnectionError,
)

from .conftest import Down

MakeTask = Callable[..., AITask[Any]]


def test_folder_triage_fails_over_to_next_model(make_task: MakeTask) -> None:
    decision = FolderTriageDecision(
        action="keep_intact", is_code=True, confidence=0.97, reasoning="Python project"
    )
    fallback = TestModel(custom_output_args=decision.model_dump())
    classifier = DriveClassifier(triage_task=make_task(FolderTriageDecision, Down(), fallback))

    res = classifier.triage_folder("homelab-service", ["main.py"], "Folder: homelab-service")
    assert res.action == "keep_intact"
    assert res.target_folder == "Code/homelab-service"


def test_total_failure_uses_confident_pre_router(make_task: MakeTask) -> None:
    classifier = DriveClassifier(document_task=make_task(DocumentClassification, Down(), Down()))
    res = classifier.classify(
        filename="checkpoint.safetensors", mime_type="application/octet-stream"
    )
    assert res.category == "Models"
    assert "LLM unreachable; pre-routing fallback" in res.reasoning


def test_total_failure_on_unidentifiable_file_raises(make_task: MakeTask) -> None:
    classifier = DriveClassifier(document_task=make_task(DocumentClassification, Down(), Down()))
    with pytest.raises(LLMConnectionError, match="LLM classification failed"):
        classifier.classify(
            filename="unidentifiable_random_junk_file.xyz", mime_type="application/octet-stream"
        )
