import logging
from dataclasses import dataclass

from homelab_ai import AISettings, AITask, LLMOutputError
from pydantic import BaseModel, Field

from .bw_client import Folder
from .items import ItemSummary

logger = logging.getLogger(__name__)

INSTRUCTIONS = """\
You file the items of a Bitwarden password vault into the owner's existing folders.
You get the list of allowed folders. Each folder shows examples of items the owner already \
filed there. Choose exactly one folder for the item.

How to decide:
1. Learn the owner's habits from the examples. If an example has the same company, website, \
or kind of item, choose that folder.
2. Otherwise, choose the folder that matches the main purpose of the service: a bank or \
insurer is finance, a store is shopping, a government site is government, an API key or \
developer platform is development or cloud.
3. Backup codes, recovery keys, and VPNs go where the examples show the owner keeps them.
4. Always choose a folder from the list, spelled exactly as listed. Never invent a folder.

Confidence:
- 0.90 or higher when an example has the same service or company.
- 0.80 to 0.90 when the purpose is clear but no example names the service.
- Below 0.80 when two folders are plausible or the item name says little.

Give a one-sentence reason."""


class FolderChoice(BaseModel):
    folder: str = Field(description="One folder name from the allowed list, spelled exactly")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence between 0.0 and 1.0")
    reason: str = Field(description="One-sentence reason for the choice")


@dataclass(frozen=True)
class Decision:
    folder: Folder
    confidence: float
    reason: str


class FolderClassifier:
    """Chooses an existing Bitwarden folder for an item with a homelab-ai task."""

    def __init__(
        self,
        settings: AISettings | None = None,
        task: AITask[FolderChoice] | None = None,
    ) -> None:
        self.task = task or AITask(
            name="bitwarden-organizer",
            output_type=FolderChoice,
            instructions=INSTRUCTIONS,
            settings=settings,
        )

    def classify(self, item: ItemSummary, folders: list[Folder], guide: str) -> Decision | None:
        """Return the chosen folder, or None when the model gives no valid folder.
        LLMConnectionError propagates so the run can stop and Kubernetes can retry."""
        try:
            choice = self.task.run_sync(
                f"Item:\n{item.describe()}",
                stable_prefix=f"Allowed folders:\n{guide}",
            )
        except LLMOutputError as exc:
            logger.warning("Model output error for item %s: %s", item.id, exc)
            return None
        by_name = {folder.name.casefold(): folder for folder in folders}
        folder = by_name.get(choice.folder.strip().casefold())
        if folder is None:
            logger.warning("Model chose unknown folder %r for item %s", choice.folder, item.id)
            return None
        return Decision(folder=folder, confidence=choice.confidence, reason=choice.reason)
