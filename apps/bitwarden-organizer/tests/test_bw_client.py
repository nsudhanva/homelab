import base64
import json
import subprocess
from typing import Any

import pytest

from bitwarden_organizer.bw_client import BitwardenCLI, BitwardenError

from .conftest import login_item


class FakeRun:
    def __init__(self, outputs: dict[str, str], fail: set[str] | None = None) -> None:
        self.outputs = outputs
        self.fail = fail or set()
        self.calls: list[dict[str, Any]] = []

    def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append({"argv": argv, **kwargs})
        command = argv[1]
        code = 1 if command in self.fail else 0
        stderr = f"{command} broke" if code else ""
        return subprocess.CompletedProcess(argv, code, self.outputs.get(command, ""), stderr)


@pytest.fixture
def cli(tmp_path: Any) -> BitwardenCLI:
    return BitwardenCLI(binary="bw", appdata_dir=str(tmp_path), server="https://vault.example")


def test_login_and_unlock_pass_secrets_in_env_only(
    cli: BitwardenCLI, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeRun({"status": json.dumps({"status": "unauthenticated"}), "unlock": "sess\n"})
    monkeypatch.setattr(subprocess, "run", fake)
    cli.login("id", "secret")
    assert cli.unlock("pw") == "sess"
    argvs = [call["argv"][1:] for call in fake.calls]
    assert argvs == [
        ["status"],
        ["config", "server", "https://vault.example"],
        ["login", "--apikey"],
        ["unlock", "--passwordenv", "BW_PASSWORD", "--raw"],
    ]
    assert fake.calls[2]["env"]["BW_CLIENTSECRET"] == "secret"
    assert fake.calls[3]["env"]["BW_PASSWORD"] == "pw"
    for call in fake.calls:
        assert "secret" not in call["argv"]
        assert "pw" not in call["argv"]
        assert call["env"]["BW_NOINTERACTION"] == "true"


def test_login_skips_when_already_logged_in(
    cli: BitwardenCLI, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeRun({"status": json.dumps({"status": "locked"})})
    monkeypatch.setattr(subprocess, "run", fake)
    cli.login("id", "secret")
    assert [call["argv"][1] for call in fake.calls] == ["status"]


def test_set_folder_sends_item_on_stdin(cli: BitwardenCLI, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeRun({})
    monkeypatch.setattr(subprocess, "run", fake)
    cli.set_folder("sess", login_item("abc", "x", "x.com"), "f-fin")
    call = fake.calls[0]
    assert call["argv"][1:] == ["edit", "item", "abc"]
    assert call["env"]["BW_SESSION"] == "sess"
    sent = json.loads(base64.b64decode(call["input"]))
    assert sent["folderId"] == "f-fin"
    assert sent["login"]["password"] == "hunter2"


def test_failed_command_raises(cli: BitwardenCLI, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", FakeRun({}, fail={"sync"}))
    with pytest.raises(BitwardenError, match="sync broke"):
        cli.sync("sess")


def test_list_folders_drops_no_folder(cli: BitwardenCLI, monkeypatch: pytest.MonkeyPatch) -> None:
    folders = [{"id": "a", "name": "Finance"}, {"id": None, "name": "No Folder"}]
    monkeypatch.setattr(subprocess, "run", FakeRun({"list": json.dumps(folders)}))
    assert [f.name for f in cli.list_folders("sess")] == ["Finance"]
