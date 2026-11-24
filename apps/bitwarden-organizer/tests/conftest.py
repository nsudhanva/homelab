from typing import Any

import pytest

from bitwarden_organizer.bw_client import Folder
from bitwarden_organizer.config import Settings

FOLDERS = [Folder(id="f-fin", name="Finance"), Folder(id="f-shop", name="Shopping")]


def login_item(item_id: str, name: str, uri: str, folder_id: str | None = None) -> dict[str, Any]:
    return {
        "id": item_id,
        "type": 1,
        "name": name,
        "folderId": folder_id,
        "notes": "secret note",
        "login": {
            "username": "me@example.com",
            "password": "hunter2",
            "uris": [{"uri": uri, "match": None}],
        },
        "fields": [{"name": "pin", "value": "1234", "type": 1}],
    }


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("BW_CLIENTID", "user.client")
    monkeypatch.setenv("BW_CLIENTSECRET", "client-secret")
    monkeypatch.setenv("BW_PASSWORD", "master-password")
    return Settings(_env_file=None)
