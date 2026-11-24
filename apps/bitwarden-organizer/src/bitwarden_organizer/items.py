from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from .bw_client import Folder

ITEM_TYPES: dict[int, str] = {
    1: "login",
    2: "secure note",
    3: "card",
    4: "identity",
    5: "ssh key",
}


@dataclass(frozen=True)
class ItemSummary:
    """The only item data that goes to the model. No passwords, notes, or field values."""

    id: str
    name: str
    kind: str
    hosts: tuple[str, ...] = field(default_factory=tuple)
    email_domain: str | None = None
    card_brand: str | None = None

    def describe(self) -> str:
        parts = [f"name: {self.name}", f"type: {self.kind}"]
        if self.hosts:
            parts.append(f"websites: {', '.join(self.hosts)}")
        if self.email_domain:
            parts.append(f"username email domain: {self.email_domain}")
        if self.card_brand:
            parts.append(f"card brand: {self.card_brand}")
        return "; ".join(parts)

    def short(self) -> str:
        host = f" ({self.hosts[0]})" if self.hosts and self.hosts[0] != self.name else ""
        return f"{self.name}{host} [{self.kind}]"


def _host(uri: str) -> str | None:
    value = uri.strip()
    if not value:
        return None
    parsed = urlsplit(value if "://" in value else f"//{value}")
    host = (parsed.hostname or "").lower()
    return host or None


def summarize(item: dict[str, Any]) -> ItemSummary:
    login = item.get("login") or {}
    hosts: list[str] = []
    for entry in login.get("uris") or []:
        host = _host(entry.get("uri") or "")
        if host and host not in hosts:
            hosts.append(host)
    username = login.get("username") or ""
    email_domain = username.rsplit("@", 1)[1].lower() if "@" in username else None
    card = item.get("card") or {}
    return ItemSummary(
        id=item["id"],
        name=(item.get("name") or "").strip() or "(no name)",
        kind=ITEM_TYPES.get(item.get("type", 0), "other"),
        hosts=tuple(hosts),
        email_domain=email_domain,
        card_brand=card.get("brand") or None,
    )


def is_active(item: dict[str, Any]) -> bool:
    return not item.get("deletedDate")


def untagged_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if is_active(item) and not item.get("folderId")]


def render_folder_guide(
    folders: list[Folder], items: list[dict[str, Any]], examples_per_folder: int
) -> str:
    """List each folder with up to N items already filed in it, so the model learns the owner's
    filing habits."""
    examples: dict[str, list[str]] = defaultdict(list)
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        folder_id = item.get("folderId")
        if not folder_id or not is_active(item):
            continue
        counts[folder_id] += 1
        if len(examples[folder_id]) < examples_per_folder:
            examples[folder_id].append(summarize(item).short())
    lines: list[str] = []
    for folder in sorted(folders, key=lambda f: f.name.lower()):
        sample = "; ".join(examples[folder.id]) if examples[folder.id] else "no items yet"
        lines.append(f"- {folder.name} ({counts[folder.id]} items). Examples: {sample}")
    return "\n".join(lines)
