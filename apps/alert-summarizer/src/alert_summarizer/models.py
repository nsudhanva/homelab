from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Alert(BaseModel):
    status: str
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None

    @property
    def alertname(self) -> str:
        return self.labels.get("alertname", "UnknownAlert")

    @property
    def severity(self) -> str:
        return self.labels.get("severity", "unknown")

    @property
    def namespace(self) -> str:
        return self.labels.get("namespace", "cluster")

    @property
    def summary(self) -> str:
        return self.annotations.get("summary", self.labels.get("alertname", "No summary provided"))

    @property
    def description(self) -> str:
        return self.annotations.get("description", "No description provided")

    @property
    def is_resolved(self) -> bool:
        return self.status.lower() == "resolved"


class AlertmanagerPayload(BaseModel):
    version: Optional[str] = None
    groupKey: Optional[str] = None
    status: str
    receiver: Optional[str] = None
    groupLabels: Dict[str, str] = Field(default_factory=dict)
    commonLabels: Dict[str, str] = Field(default_factory=dict)
    commonAnnotations: Dict[str, str] = Field(default_factory=dict)
    externalURL: Optional[str] = None
    alerts: List[Alert] = Field(default_factory=list)
