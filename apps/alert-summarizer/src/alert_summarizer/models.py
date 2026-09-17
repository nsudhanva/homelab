from pydantic import BaseModel, Field


class Alert(BaseModel):
    status: str
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: str | None = None
    endsAt: str | None = None
    generatorURL: str | None = None
    fingerprint: str | None = None

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
    version: str | None = None
    groupKey: str | None = None
    status: str
    receiver: str | None = None
    groupLabels: dict[str, str] = Field(default_factory=dict)
    commonLabels: dict[str, str] = Field(default_factory=dict)
    commonAnnotations: dict[str, str] = Field(default_factory=dict)
    externalURL: str | None = None
    alerts: list[Alert] = Field(default_factory=list)


class AlertSummary(BaseModel):
    symptom: str = Field(
        description="Concise description of the affected Kubernetes component or service symptom"
    )
    probable_cause: str = Field(
        description="Immediate probable root cause inferred from annotations and metrics"
    )
    recommended_action: str = Field(
        description="Precise triage command (e.g. kubectl command) or immediate remediation step"
    )
