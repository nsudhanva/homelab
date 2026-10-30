import logging

from homelab_ai import AITask, HomelabAIError

from ..models import AlertSummary

logger = logging.getLogger(__name__)


def alert_instructions(cluster_name: str, environment: str) -> str:
    return (
        "You are an expert Site Reliability Engineering (SRE) on-call assistant "
        "for a bare-metal Kubernetes homelab cluster. "
        "Analyze the alert name, severity, labels, annotations, and timestamps. "
        "Extract a concise, high-signal operational summary with:\n"
        "1. symptom: Brief description of the observed issue or failure state.\n"
        "2. probable_cause: Most likely root cause based on the alert context.\n"
        "3. recommended_action: Immediate, practical triage or fix command (e.g. kubectl).\n"
        f"Target Cluster: {cluster_name} | Environment: {environment.upper()}\n"
        "Prioritize commands targeting the appropriate namespace and resources."
    )


class AlertAgentClient:
    def __init__(
        self,
        cluster_name: str = "homelab-k3s",
        environment: str = "production",
        task: AITask[AlertSummary] | None = None,
    ):
        self.task = task or AITask(
            name="alert-summarizer",
            output_type=AlertSummary,
            instructions=alert_instructions(cluster_name, environment),
        )

    async def summarize_alert(
        self,
        alert_context: str,
        is_resolved: bool,
    ) -> AlertSummary | None:
        user_prompt = (
            f"Alert State: {'RESOLVED' if is_resolved else 'FIRING'}\n\n"
            f"Alert Context:\n{alert_context}"
        )
        try:
            return await self.task.run(user_prompt)
        except HomelabAIError as exc:
            logger.warning(f"Alert summarization failed: {exc}")
            return None
