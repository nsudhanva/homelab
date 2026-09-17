import logging
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from ..models import AlertSummary

logger = logging.getLogger(__name__)


@dataclass
class SummarizerDeps:
    cluster_name: str = "homelab-k3s"
    environment: str = "production"


def build_alert_agent(
    model: Model | str,
    retries: int = 2,
) -> Agent[SummarizerDeps, AlertSummary]:
    agent: Agent[SummarizerDeps, AlertSummary] = Agent(
        model=model,
        output_type=AlertSummary,
        deps_type=SummarizerDeps,
        system_prompt=(
            "You are an expert Site Reliability Engineering (SRE) on-call assistant "
            "for a bare-metal Kubernetes homelab cluster. "
            "Analyze the alert name, severity, labels, annotations, and timestamps. "
            "Extract a concise, high-signal operational summary with:\n"
            "1. symptom: Brief description of the observed issue or failure state.\n"
            "2. probable_cause: Most likely root cause based on the alert context.\n"
            "3. recommended_action: Immediate, practical triage or fix command (e.g. kubectl).\n"
        ),
        retries=retries,
    )

    @agent.system_prompt
    def cluster_context(ctx: RunContext[SummarizerDeps]) -> str:
        env = ctx.deps.environment.upper()
        return (
            f"Target Cluster: {ctx.deps.cluster_name} | Environment: {env}\n"
            "Prioritize commands targeting the appropriate namespace and resources."
        )

    return agent


class AlertAgentClient:
    def __init__(
        self,
        base_url: str,
        model_name: str,
        retries: int = 2,
        cluster_name: str = "homelab-k3s",
        environment: str = "production",
        custom_model: Model | None = None,
    ):
        self.cluster_name = cluster_name
        self.environment = environment

        if custom_model is not None:
            self._model = custom_model
        else:
            provider = OpenAIProvider(
                base_url=base_url.rstrip("/"),
                api_key="none",
            )
            self._model = OpenAIChatModel(
                model_name=model_name,
                provider=provider,
            )

        self.agent = build_alert_agent(model=self._model, retries=retries)

    async def summarize_alert(
        self,
        alert_context: str,
        is_resolved: bool,
    ) -> AlertSummary | None:
        user_prompt = (
            f"Alert State: {'RESOLVED' if is_resolved else 'FIRING'}\n\n"
            f"Alert Context:\n{alert_context}"
        )
        deps = SummarizerDeps(
            cluster_name=self.cluster_name,
            environment=self.environment,
        )

        try:
            res = await self.agent.run(user_prompt, deps=deps)
            return res.output
        except Exception as exc:
            logger.warning(f"Pydantic AI alert summarization failed: {exc}")
            return None
