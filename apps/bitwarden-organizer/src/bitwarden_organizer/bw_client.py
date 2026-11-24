import base64
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

STDERR_LIMIT = 300


class BitwardenError(Exception):
    """A Bitwarden CLI command failed."""


@dataclass(frozen=True)
class Folder:
    id: str
    name: str


class BitwardenCLI:
    """Thin wrapper around the `bw` CLI. Secrets go through the environment, never argv."""

    def __init__(
        self,
        binary: str = "bw",
        appdata_dir: str = "/tmp/bitwarden",
        server: str | None = None,
        timeout: int = 180,
    ) -> None:
        self.binary = binary
        self.appdata_dir = appdata_dir
        self.server = server
        self.timeout = timeout

    def _env(self, session: str | None, extra: dict[str, str] | None) -> dict[str, str]:
        env = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", self.appdata_dir),
            "BITWARDENCLI_APPDATA_DIR": self.appdata_dir,
            "BW_NOINTERACTION": "true",
        }
        if session:
            env["BW_SESSION"] = session
        if extra:
            env.update(extra)
        return env

    def _run(
        self,
        *args: str,
        session: str | None = None,
        extra_env: dict[str, str] | None = None,
        stdin_text: str | None = None,
    ) -> str:
        os.makedirs(self.appdata_dir, exist_ok=True)
        try:
            result = subprocess.run(
                [self.binary, *args],
                env=self._env(session, extra_env),
                input=stdin_text,
                stdin=None if stdin_text is not None else subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise BitwardenError(f"bw {args[0]} timed out after {self.timeout}s") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()[:STDERR_LIMIT]
            raise BitwardenError(f"bw {args[0]} failed: {detail}")
        return result.stdout

    def status(self) -> str:
        return json.loads(self._run("status"))["status"]

    def login(self, client_id: str, client_secret: str) -> None:
        if self.status() != "unauthenticated":
            return
        if self.server:
            self._run("config", "server", self.server)
        self._run(
            "login",
            "--apikey",
            extra_env={"BW_CLIENTID": client_id, "BW_CLIENTSECRET": client_secret},
        )

    def unlock(self, password: str) -> str:
        session = self._run(
            "unlock",
            "--passwordenv",
            "BW_PASSWORD",
            "--raw",
            extra_env={"BW_PASSWORD": password},
        ).strip()
        if not session:
            raise BitwardenError("bw unlock returned no session key")
        return session

    def sync(self, session: str) -> None:
        self._run("sync", session=session)

    def list_folders(self, session: str) -> list[Folder]:
        raw = json.loads(self._run("list", "folders", session=session))
        return [Folder(id=f["id"], name=f["name"]) for f in raw if f.get("id")]

    def list_items(self, session: str) -> list[dict[str, Any]]:
        return json.loads(self._run("list", "items", session=session))

    def set_folder(self, session: str, item: dict[str, Any], folder_id: str) -> None:
        payload = json.dumps({**item, "folderId": folder_id})
        encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        self._run("edit", "item", item["id"], session=session, stdin_text=encoded)

    def lock(self) -> None:
        try:
            self._run("lock")
        except BitwardenError as exc:
            logger.warning("Could not lock the vault: %s", exc)
