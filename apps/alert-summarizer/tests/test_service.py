import os
from unittest.mock import AsyncMock

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

from alert_summarizer.clients import AlertAgentClient, TelegramClient
from alert_summarizer.models import Alert, AlertmanagerPayload, AlertSummary
from alert_summarizer.service import AlertSummarizerService

os.environ["PYDANTIC_AI_NO_BANNER"] = "1"


@pytest.fixture
def sample_alert() -> Alert:
    return Alert(
        status="firing",
        labels={
            "alertname": "KubePodCrashLooping",
            "namespace": "monitoring",
            "pod": "test-pod-123",
            "severity": "critical",
        },
        annotations={
            "summary": "Pod test-pod-123 is crash looping",
            "description": "Restarted 5 times in 10 minutes",
        },
    )


@pytest.fixture
def sample_resolved_alert() -> Alert:
    return Alert(
        status="resolved",
        labels={
            "alertname": "KubePodCrashLooping",
            "namespace": "monitoring",
            "pod": "test-pod-123",
            "severity": "critical",
        },
        annotations={
            "summary": "Pod test-pod-123 is healthy",
            "description": "Pod recovered",
        },
    )


def test_format_alert_context(sample_alert: Alert):
    service = AlertSummarizerService(agent_client=AsyncMock(), telegram_client=AsyncMock())
    ctx = service.format_alert_context(sample_alert)
    assert "Alert: KubePodCrashLooping" in ctx
    assert "Namespace: monitoring" in ctx
    assert "Severity: critical" in ctx
    assert "Restarted 5 times in 10 minutes" in ctx


def test_format_fallback_message(sample_alert: Alert):
    service = AlertSummarizerService(agent_client=AsyncMock(), telegram_client=AsyncMock())
    msg = service.format_fallback_message(sample_alert)
    assert "🔴 <b>[FIRING] KubePodCrashLooping</b>" in msg
    assert "<code>monitoring</code>" in msg
    assert "Pod test-pod-123 is crash looping" in msg


def test_format_fallback_message_resolved(sample_resolved_alert: Alert):
    service = AlertSummarizerService(agent_client=AsyncMock(), telegram_client=AsyncMock())
    msg = service.format_fallback_message(sample_resolved_alert)
    assert "🟢 <b>[RESOLVED] KubePodCrashLooping</b>" in msg


@pytest.mark.asyncio
async def test_pydantic_ai_agent_direct_test_model():
    client = AlertAgentClient(
        base_url="http://localhost:8080/v1",
        model_name="gemma-4-e2b-it",
        custom_model=TestModel(),
    )
    summary = await client.summarize_alert("Pod crash looping context", is_resolved=False)
    assert summary is not None
    assert isinstance(summary, AlertSummary)
    assert summary.symptom != ""
    assert summary.probable_cause != ""
    assert summary.recommended_action != ""


@pytest.mark.asyncio
async def test_process_alert_with_pydantic_ai_success(sample_alert: Alert):
    def structured_model(messages, info):
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="final_result",
                    args={
                        "symptom": "Pod test-pod-123 crashing continuously",
                        "probable_cause": "OOMKilled due to memory limit reached",
                        "recommended_action": "kubectl describe pod test-pod-123 -n monitoring",
                    },
                )
            ]
        )

    agent_client = AlertAgentClient(
        base_url="http://localhost:8080/v1",
        model_name="gemma-4-e2b-it",
        custom_model=FunctionModel(structured_model),
    )
    mock_tg = AsyncMock(spec=TelegramClient)
    mock_tg.send_message.return_value = True

    service = AlertSummarizerService(agent_client=agent_client, telegram_client=mock_tg)
    success = await service.process_alert(sample_alert)

    assert success is True
    mock_tg.send_message.assert_awaited_once()
    sent_text = mock_tg.send_message.call_args[0][0]
    assert "🔴 <b>[FIRING] KubePodCrashLooping</b>" in sent_text
    assert "• <b>Symptom:</b> Pod test-pod-123 crashing continuously" in sent_text
    assert "• <b>Cause:</b> OOMKilled due to memory limit reached" in sent_text
    assert "• <b>Action:</b> kubectl describe pod test-pod-123 -n monitoring" in sent_text


@pytest.mark.asyncio
async def test_process_alert_with_agent_fallback(sample_alert: Alert):
    mock_agent = AsyncMock(spec=AlertAgentClient)
    mock_agent.summarize_alert.return_value = None
    mock_tg = AsyncMock(spec=TelegramClient)
    mock_tg.send_message.return_value = True

    service = AlertSummarizerService(agent_client=mock_agent, telegram_client=mock_tg)
    success = await service.process_alert(sample_alert)

    assert success is True
    mock_tg.send_message.assert_awaited_once()
    sent_text = mock_tg.send_message.call_args[0][0]
    assert "🔴 <b>[FIRING] KubePodCrashLooping</b>" in sent_text
    assert "Summary" in sent_text
    assert "Restarted 5 times in 10 minutes" in sent_text


@pytest.mark.asyncio
async def test_process_payload(sample_alert: Alert):
    mock_agent = AsyncMock(spec=AlertAgentClient)
    mock_agent.summarize_alert.return_value = AlertSummary(
        symptom="Component failure",
        probable_cause="Node pressure",
        recommended_action="kubectl get nodes",
    )
    mock_tg = AsyncMock(spec=TelegramClient)
    mock_tg.send_message.return_value = True

    payload = AlertmanagerPayload(
        status="firing",
        alerts=[sample_alert, sample_alert],
    )

    service = AlertSummarizerService(agent_client=mock_agent, telegram_client=mock_tg)
    count = await service.process_payload(payload)

    assert count == 2
    assert mock_tg.send_message.await_count == 2
