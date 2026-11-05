from unittest.mock import MagicMock

import pytest

from drive_organizer.classifier import DocumentClassification, DriveClassifier, FolderTriageDecision
from drive_organizer.drive_client import DriveClient
from drive_organizer.pre_router import PreRouter

from .conftest import Down


def test_list_unorganized_root_folders_filters_protected():
    client = DriveClient(
        client_id="dummy",
        client_secret="dummy",
        refresh_token="dummy",
    )
    mock_files = [
        {"id": "id1", "name": "Sudhanva"},
        {"id": "id2", "name": "Maanasa"},
        {"id": "id3", "name": "Code"},
        {"id": "id4", "name": "Media"},
        {"id": "id5", "name": "Review"},
        {"id": "id6", "name": "folder 1"},
        {"id": "id7", "name": "2024 Taxes"},
        {"id": "id8", "name": "Taxes 2024"},
    ]
    mock_service = MagicMock()
    mock_service.files().list().execute.return_value = {"files": mock_files}
    client.service = mock_service

    unorganized = client.list_unorganized_root_folders()
    names = [f["name"] for f in unorganized]
    assert names == ["folder 1", "2024 Taxes", "Taxes 2024"]


@pytest.mark.parametrize(
    ("folder_name", "sample_files", "tree_summary", "action", "is_code", "target_folder"),
    [
        pytest.param(
            "homelab-service",
            ["src/main.py", "pyproject.toml", "README.md"],
            "Folder: homelab-service\n  📁 src/\n    📄 main.py\n  📄 pyproject.toml",
            "keep_intact",
            True,
            "Code/homelab-service",
            id="code-kept-intact",
        ),
        pytest.param(
            "ml-experiments",
            ["data.csv", "exploration.ipynb"],
            "Folder: ml-experiments\n  📄 data.csv\n  📄 exploration.ipynb",
            "keep_intact",
            True,
            "Colab Notebooks/ml-experiments",
            id="notebooks-kept-intact",
        ),
        pytest.param(
            "folder 1",
            ["sub folder 1/dummy.pdf", "receipt.png"],
            "Folder: folder 1\n  📁 sub folder 1/\n    📄 dummy.pdf",
            "dismantle",
            False,
            None,
            id="documents-dismantled",
        ),
    ],
)
def test_folder_triage_heuristics_when_model_is_down(
    make_task, folder_name, sample_files, tree_summary, action, is_code, target_folder
):
    classifier = DriveClassifier(triage_task=make_task(FolderTriageDecision, Down()))
    decision = classifier.triage_folder(
        folder_name=folder_name, sample_files=sample_files, tree_summary=tree_summary
    )
    assert decision.action == action
    assert decision.is_code is is_code
    assert decision.target_folder == target_folder


def test_walk_folder_files_and_dirs():
    client = DriveClient(
        client_id="dummy",
        client_secret="dummy",
        refresh_token="dummy",
    )
    mock_service = MagicMock()

    # Root folder contents: sub folder 1
    # Sub folder 1 contents: dummy.pdf
    def mock_list(q: str, **kwargs):
        req = MagicMock()
        if "'root-id'" in q:
            req.execute.return_value = {
                "files": [
                    {
                        "id": "sub-id",
                        "name": "sub folder 1",
                        "mimeType": "application/vnd.google-apps.folder",
                    }
                ]
            }
        elif "'sub-id'" in q:
            req.execute.return_value = {
                "files": [
                    {
                        "id": "pdf-id",
                        "name": "dummy.pdf",
                        "mimeType": "application/pdf",
                        "parents": ["sub-id"],
                    }
                ]
            }
        else:
            req.execute.return_value = {"files": []}
        return req

    mock_service.files().list.side_effect = mock_list
    client.service = mock_service

    files_to_process, folders_to_prune = client.walk_folder_files_and_dirs("root-id", "folder 1")

    assert len(files_to_process) == 1
    assert files_to_process[0]["name"] == "dummy.pdf"
    assert files_to_process[0]["folder_breadcrumbs"] == ["folder 1", "sub folder 1"]

    # Prune order must be deepest leaf first: sub folder 1, then folder 1
    assert len(folders_to_prune) == 2
    assert folders_to_prune[0]["name"] == "sub folder 1"
    assert folders_to_prune[1]["name"] == "folder 1"


def test_prune_empty_folders():
    client = DriveClient(
        client_id="dummy",
        client_secret="dummy",
        refresh_token="dummy",
    )
    mock_service = MagicMock()

    # sub-id is empty, root-id has 1 file
    def mock_list(q: str, **kwargs):
        req = MagicMock()
        if "'sub-id'" in q:
            req.execute.return_value = {"files": []}
        elif "'root-id'" in q:
            req.execute.return_value = {"files": [{"id": "remaining-file"}]}
        return req

    mock_service.files().list.side_effect = mock_list
    client.service = mock_service

    folders = [
        {"id": "sub-id", "name": "sub folder 1", "depth": 1},
        {"id": "root-id", "name": "folder 1", "depth": 0},
    ]

    pruned = client.prune_empty_folders(folders, dry_run=False)
    assert pruned == ["sub folder 1"]
    mock_service.files().update.assert_called_once_with(fileId="sub-id", body={"trashed": True})


def test_pre_router_with_folder_breadcrumbs():
    res = PreRouter.analyze(
        filename="w2.pdf",
        extracted_text="Some wage statement",
        folder_breadcrumbs=["2024 Taxes", "Personal"],
    )
    assert res.category == "Taxes"
    assert res.subcategory == "2024"


def test_nested_file_move_with_model_fallback(make_task):
    """Walk a nested folder, classify its file with an injected fallback model, move it, and prune."""
    from pydantic_ai.models.test import TestModel

    from drive_organizer.config import Settings
    from drive_organizer.main import process_single_file
    from drive_organizer.notifier import OrganizerRunStats

    client = DriveClient(
        client_id="dummy",
        client_secret="dummy",
        refresh_token="dummy",
    )
    mock_service = MagicMock()

    # Simulate Google Drive file hierarchy:
    # 'root-id' (folder 1) -> contains 'sub-id' (sub folder 1)
    # 'sub-id' -> contains 'dummy-pdf-id' (dummy.pdf)
    def mock_list(q: str = "", **kwargs):
        req = MagicMock()
        if "'root-id' in parents" in q and "trashed = false" in q:
            # During walk, root-id contains sub-id.
            # During prune check (if checked after sub folder trashed or if simulated empty),
            # we return empty list to simulate clean dismantling
            if kwargs.get("pageSize") == 1:
                req.execute.return_value = {"files": []}
            else:
                req.execute.return_value = {
                    "files": [
                        {
                            "id": "sub-id",
                            "name": "sub folder 1",
                            "mimeType": "application/vnd.google-apps.folder",
                        }
                    ]
                }
        elif "'sub-id' in parents" in q and "trashed = false" in q:
            if kwargs.get("pageSize") == 1:
                # During prune check, dummy.pdf was moved, so sub folder is empty
                req.execute.return_value = {"files": []}
            else:
                req.execute.return_value = {
                    "files": [
                        {
                            "id": "dummy-pdf-id",
                            "name": "dummy.pdf",
                            "mimeType": "application/pdf",
                            "parents": ["sub-id"],
                        }
                    ]
                }
        else:
            req.execute.return_value = {"files": []}
        return req

    mock_service.files().list.side_effect = mock_list
    client.service = mock_service

    files_to_process, folders_to_prune = client.walk_folder_files_and_dirs("root-id", "folder 1")
    assert len(files_to_process) == 1
    file_info = files_to_process[0]
    assert file_info["name"] == "dummy.pdf"
    assert file_info["folder_breadcrumbs"] == ["folder 1", "sub folder 1"]
    assert len(folders_to_prune) == 2
    assert folders_to_prune[0]["name"] == "sub folder 1"
    assert folders_to_prune[1]["name"] == "folder 1"

    fallback_output = {
        "person": "Sudhanva",
        "jurisdiction": "USA",
        "category": "Career",
        "subcategory": "Interview Prep",
        "clean_filename": "dummy_clean.pdf",
        "is_joint": False,
        "confidence": 0.95,
        "summary": "Processed dummy.pdf with the fallback model",
        "search_tags": ["notes", "interview"],
        "reasoning": "Fallback model succeeded after local endpoint failure",
    }
    fallback_model = TestModel(custom_output_args=fallback_output, model_name="fallback")

    classifier = DriveClassifier(
        document_task=make_task(DocumentClassification, Down(), fallback_model)
    )

    client.download_file_header_bytes = MagicMock(return_value=b"%PDF-1.4 simulated pdf stream")
    client.get_or_create_path = MagicMock(return_value="target-folder-id")
    client.move_and_tag_file = MagicMock()

    settings = Settings(pacing_seconds=0.0)
    stats = OrganizerRunStats()

    success = process_single_file(
        file_info=file_info,
        drive_client=client,
        classifier=classifier,
        settings=settings,
        stats=stats,
        dry_run=False,
    )

    assert success is True
    assert stats.total_docs_classified == 1
    assert len(stats.errors) == 0
    assert any("dummy_clean.pdf" in a for a in stats.actions)

    client.move_and_tag_file.assert_called_once_with(
        file_id="dummy-pdf-id",
        new_name="dummy_clean.pdf",
        target_folder_id="target-folder-id",
        current_parents=["sub-id"],
        description="Processed dummy.pdf with the fallback model",
        search_tags=["notes", "interview"],
    )

    pruned = client.prune_empty_folders(folders_to_prune, dry_run=False)
    assert pruned == ["sub folder 1", "folder 1"]
    assert mock_service.files().update.call_count == 2
