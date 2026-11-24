from typing import Any

from homelab_ai import LLMConnectionError

from bitwarden_organizer.bw_client import BitwardenError, Folder
from bitwarden_organizer.classifier import Decision
from bitwarden_organizer.config import Settings
from bitwarden_organizer.items import ItemSummary
from bitwarden_organizer.main import organize, parse_arguments
from bitwarden_organizer.notifier import TelegramNotifier

from .conftest import FOLDERS, login_item


class FakeCLI:
    def __init__(self, items: list[dict[str, Any]], fail_ids: set[str] | None = None) -> None:
        self.items = items
        self.fail_ids = fail_ids or set()
        self.moved: dict[str, str] = {}
        self.events: list[str] = []

    def login(self, client_id: str, client_secret: str) -> None:
        self.events.append("login")

    def unlock(self, password: str) -> str:
        self.events.append("unlock")
        return "sess"

    def sync(self, session: str) -> None:
        self.events.append("sync")

    def list_folders(self, session: str) -> list[Folder]:
        return FOLDERS

    def list_items(self, session: str) -> list[dict[str, Any]]:
        return self.items

    def set_folder(self, session: str, item: dict[str, Any], folder_id: str) -> None:
        if item["id"] in self.fail_ids:
            raise BitwardenError("edit failed")
        self.moved[item["id"]] = folder_id

    def lock(self) -> None:
        self.events.append("lock")


class FakeClassifier:
    def __init__(self, answers: dict[str, str | None], down_after: int | None = None) -> None:
        self.answers = answers
        self.down_after = down_after
        self.calls = 0

    def classify(self, item: ItemSummary, folders: list[Folder], guide: str) -> Decision | None:
        self.calls += 1
        if self.down_after is not None and self.calls > self.down_after:
            raise LLMConnectionError("down")
        name = self.answers.get(item.name)
        folder = next((f for f in folders if f.name == name), None)
        return Decision(folder=folder, confidence=0.7, reason="r") if folder else None


ITEMS = [
    login_item("1", "costco.com", "costco.com"),
    login_item("2", "chase.com", "chase.com"),
    login_item("3", "mystery", "mystery.example"),
    login_item("4", "amex.com", "amex.com", folder_id="f-fin"),
]
ANSWERS: dict[str, str | None] = {"costco.com": "Shopping", "chase.com": "Finance"}


def run(cli: Any, classifier: Any, settings: Settings, **kwargs: Any):
    return organize(cli, classifier, settings, **kwargs)


def test_files_untagged_items_and_locks(settings: Settings) -> None:
    cli = FakeCLI(ITEMS)
    report = run(cli, FakeClassifier(ANSWERS), settings)
    assert cli.moved == {"1": "f-shop", "2": "f-fin"}
    assert report.untagged == 3
    assert report.skipped == ["mystery"]
    assert report.folder_counts() == {"Shopping": 1, "Finance": 1}
    assert cli.events == ["login", "unlock", "sync", "sync", "lock"]


def test_dry_run_changes_nothing(settings: Settings) -> None:
    cli = FakeCLI(ITEMS)
    report = run(cli, FakeClassifier(ANSWERS), settings, dry_run=True)
    assert cli.moved == {}
    assert len(report.filed) == 2
    assert cli.events[-1] == "lock"


def test_limit_and_edit_failure(settings: Settings) -> None:
    cli = FakeCLI(ITEMS, fail_ids={"1"})
    report = run(cli, FakeClassifier(ANSWERS), settings, limit=2)
    assert report.failed == ["costco.com"]
    assert cli.moved == {"2": "f-fin"}


def test_model_outage_stops_run_and_still_locks(settings: Settings) -> None:
    cli = FakeCLI(ITEMS)
    report = run(cli, FakeClassifier(ANSWERS, down_after=1), settings)
    assert report.error == "No model answered"
    assert cli.moved == {"1": "f-shop"}
    assert cli.events[-1] == "lock"


def test_summary_lists_low_confidence(settings: Settings) -> None:
    report = run(FakeCLI(ITEMS), FakeClassifier(ANSWERS), settings)
    text = "\n".join(TelegramNotifier(None, 1).format_summary(report, 0.8))
    assert "Filed:</b> 2" in text
    assert "Low confidence, check these (2)" in text
    assert "mystery" in text
    assert "hunter2" not in text


def test_parse_arguments() -> None:
    args = parse_arguments(["--dry-run", "--limit", "5"])
    assert args.dry_run is True
    assert args.limit == 5
