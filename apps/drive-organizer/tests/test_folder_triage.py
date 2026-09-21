from unittest.mock import MagicMock

from drive_organizer.classifier import DriveClassifier, FolderTriageDecision
from drive_organizer.drive_client import PROTECTED_ROOT_FOLDERS, DriveClient
from drive_organizer.pre_router import PreRouter


def test_protected_root_folders():
    assert "sudhanva" in PROTECTED_ROOT_FOLDERS
    assert "maanasa" in PROTECTED_ROOT_FOLDERS
    assert "media" in PROTECTED_ROOT_FOLDERS
    assert "code" in PROTECTED_ROOT_FOLDERS
    assert "review" in PROTECTED_ROOT_FOLDERS
    assert "folder 1" not in PROTECTED_ROOT_FOLDERS
    assert "taxes 2024" not in PROTECTED_ROOT_FOLDERS


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
        {"id": "id4", "name": "folder 1"},
        {"id": "id5", "name": "2024 Taxes"},
    ]
    mock_service = MagicMock()
    mock_service.files().list().execute.return_value = {"files": mock_files}
    client.service = mock_service

    unorganized = client.list_unorganized_root_folders()
    names = [f["name"] for f in unorganized]
    assert "folder 1" in names
    assert "2024 Taxes" in names
    assert "Sudhanva" not in names
    assert "Maanasa" not in names
    assert "Code" not in names


def test_folder_triage_heuristics_code_intact():
    class FailingAgent:
        def run_sync(self, prompt: str):
            raise RuntimeError("LLM offline")

    classifier = DriveClassifier(triage_agent=FailingAgent())  # type: ignore[arg-type]
    decision = classifier.triage_folder_sync(
        folder_name="homelab-service",
        sample_files=["src/main.py", "pyproject.toml", "README.md"],
        tree_summary="Folder: homelab-service\n  📁 src/\n    📄 main.py\n  📄 pyproject.toml",
    )
    assert decision.action == "keep_intact"
    assert decision.is_code is True
    assert decision.target_folder == "Code/homelab-service"


def test_folder_triage_heuristics_notebooks_intact():
    class FailingAgent:
        def run_sync(self, prompt: str):
            raise RuntimeError("LLM offline")

    classifier = DriveClassifier(triage_agent=FailingAgent())  # type: ignore[arg-type]
    decision = classifier.triage_folder_sync(
        folder_name="ml-experiments",
        sample_files=["data.csv", "exploration.ipynb"],
        tree_summary="Folder: ml-experiments\n  📄 data.csv\n  📄 exploration.ipynb",
    )
    assert decision.action == "keep_intact"
    assert decision.is_code is True
    assert decision.target_folder == "Colab Notebooks/ml-experiments"


def test_folder_triage_heuristics_documents_dismantle():
    class FailingAgent:
        def run_sync(self, prompt: str):
            raise RuntimeError("LLM offline")

    classifier = DriveClassifier(triage_agent=FailingAgent())  # type: ignore[arg-type]
    decision = classifier.triage_folder_sync(
        folder_name="folder 1",
        sample_files=["sub folder 1/dummy.pdf", "receipt.png"],
        tree_summary="Folder: folder 1\n  📁 sub folder 1/\n    📄 dummy.pdf",
    )
    assert decision.action == "dismantle"
    assert decision.is_code is False
    assert decision.target_folder is None


def test_folder_triage_mock_agent():
    mock_decision = FolderTriageDecision(
        action="dismantle",
        is_code=False,
        target_folder=None,
        confidence=0.99,
        reasoning="Document batch for personal organization.",
    )

    class MockAgent:
        def run_sync(self, prompt: str):
            class Res:
                output = mock_decision

            return Res()

    classifier = DriveClassifier(triage_agent=MockAgent())  # type: ignore[arg-type]
    decision = classifier.triage_folder_sync(
        folder_name="Scans",
        sample_files=["scan1.pdf"],
        tree_summary="Folder: Scans\n  📄 scan1.pdf",
    )
    assert decision.action == "dismantle"
    assert decision.confidence == 0.99


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


def test_end_to_end_process_dummy_pdf_inside_folder1_subfolder1_with_fallback():
    """Verify end-to-end processing of dummy.pdf inside folder 1 > sub folder 1 with model fallback to OpenRouter."""
    from pydantic_ai.exceptions import ModelAPIError
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

    # 1. Walk folder discovers dummy.pdf and produces deepest-leaf-first prune order
    files_to_process, folders_to_prune = client.walk_folder_files_and_dirs("root-id", "folder 1")
    assert len(files_to_process) == 1
    file_info = files_to_process[0]
    assert file_info["name"] == "dummy.pdf"
    assert file_info["folder_breadcrumbs"] == ["folder 1", "sub folder 1"]
    assert len(folders_to_prune) == 2
    assert folders_to_prune[0]["name"] == "sub folder 1"
    assert folders_to_prune[1]["name"] == "folder 1"

    # 2. Simulate crashed local LLM endpoint (502 Connection Refused)
    class FailingLocalModel(TestModel):
        async def request(self, *args, **kwargs):
            raise ModelAPIError(model_name="gemma-4-e2b-it", message="Connection Refused 502")

    # Fallback model routes to OpenRouter Gemma 4 31B
    openrouter_output = {
        "person": "Sudhanva",
        "jurisdiction": "USA",
        "category": "Career",
        "subcategory": "Interview Prep",
        "clean_filename": "dummy_clean.pdf",
        "is_joint": False,
        "confidence": 0.95,
        "summary": "Processed dummy.pdf routed via OpenRouter Gemma 4 31B",
        "search_tags": ["notes", "interview"],
        "reasoning": "Fallback to OpenRouter Gemma 4 31B succeeded after local endpoint failure",
    }
    openrouter_model = TestModel(
        custom_output_args=openrouter_output,
        model_name="google/gemma-4-31b-it",
    )

    classifier = DriveClassifier(
        primary_model=FailingLocalModel(),
        fallback_model=openrouter_model,
    )

    client.download_file_header_bytes = MagicMock(return_value=b"%PDF-1.4 simulated pdf stream")
    client.get_or_create_path = MagicMock(return_value="target-folder-id")
    client.move_and_tag_file = MagicMock()

    settings = Settings(pacing_seconds=0.0)
    stats = OrganizerRunStats()

    # 3. Process dummy.pdf through full inspection, fallback classification, move and tag
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
        description="Processed dummy.pdf routed via OpenRouter Gemma 4 31B",
        search_tags=["notes", "interview"],
    )

    # 4. Prune empty folder shells (leaf first: sub folder 1, then folder 1)
    pruned = client.prune_empty_folders(folders_to_prune, dry_run=False)
    assert pruned == ["sub folder 1", "folder 1"]
    assert mock_service.files().update.call_count == 2
