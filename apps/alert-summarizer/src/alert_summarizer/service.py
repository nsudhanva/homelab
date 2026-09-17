import html
import logging
from typing import Optional

from .clients import LLMClient, TelegramClient
from .models import Alert, AlertmanagerPayload

logger = logging.getLogger(__name__)


class AlertSummarizerService:
    def __init__(self, llm_client: LLMClient, telegram_client: TelegramClient):
        self.llm = llm_client
        self.telegram = telegram_client

    def format_alert_context(self, alert: Alert) -> str:
        lines = [
            f"Alert: {alert.alertname}",
            f"Namespace: {alert.namespace}",
            f"Severity: {alert.severity}",
            f"Summary: {alert.summary}",
            f"Description: {alert.description}",
        ]
        relevant_labels = {
            k: v for k, v in alert.labels.items()
            if k not in {"alertname", "namespace", "severity", "prometheus", "endpoint"}
        }
        if relevant_labels:
            labels_str = ", ".join(f"{k}={v}" for k, v in list(relevant_labels.items())[:5])
            lines.append(f"Labels: {labels_str}")
        return "\n".join(lines)

    def format_fallback_message(self, alert: Alert) -> str:
        status_emoji = "🟢" if alert.is_resolved else ("🔴" if alert.severity == "critical" else "🟡")
        status_text = "RESOLVED" if alert.is_resolved else "FIRING"

        safe_alertname = html.escape(alert.alertname)
        safe_namespace = html.escape(alert.namespace)
        safe_severity = html.escape(alert.severity.upper())
        safe_summary = html.escape(alert.summary)
        safe_desc = html.escape(alert.description)

        return (
            f"{status_emoji} <b>[{status_text}] {safe_alertname}</b>\n"
            f"• <b>Namespace</b>: <code>{safe_namespace}</code>\n"
            f"• <b>Severity</b>: {safe_severity}\n"
            f"• <b>Summary</b>: {safe_summary}\n"
            f"• <b>Description</b>: {safe_desc}"
        )

    def format_ai_message(self, alert: Alert, ai_summary: str) -> str:
        status_emoji = "🟢" if alert.is_resolved else ("🔴" if alert.severity == "critical" else "🟡")
        status_text = "RESOLVED" if alert.is_resolved else "FIRING"
        safe_alertname = html.escape(alert.alertname)
        safe_namespace = html.escape(alert.namespace)

        return (
            f"{status_emoji} <b>[{status_text}] {safe_alertname}</b> (<code>{safe_namespace}</code>)\n\n"
            f"{ai_summary}"
        )

    async def process_alert(self, alert: Alert) -> bool:
        alert_context = self.format_alert_context(alert)
        logger.info(f"Processing alert: {alert.alertname} (status={alert.status})")

        # Attempt AI summarization via local Gemma 4
        ai_summary = await self.llm.summarize_alert(alert_context, alert.is_resolved)

        if ai_summary:
            logger.info(f"AI summarization succeeded for {alert.alertname}")
            msg = self.format_ai_message(alert, ai_summary)
        else:
            logger.warning(f"Using fallback template for {alert.alertname}")
            msg = self.format_fallback_message(alert)

        return await self.telegram.send_message(msg)

    async def process_payload(self, payload: AlertmanagerPayload) -> int:
        success_count = 0
        for alert in payload.alerts:
            if await self.process_alert(alert):
                success_count += 1
        return success_count
