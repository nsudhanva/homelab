from unittest.mock import AsyncMock, patch
import pytest

from alert_summarizer.clients import LLMClient, TelegramClient
from alert_summarizer.models import Alert, AlertmanagerPayload
from alert_summarizer.service import AlertSummarizerService


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
    service = AlertSummarizerService(llm_client=AsyncMock(), telegram_client=AsyncMock())
    ctx = service.format_alert_context(sample_alert)
    assert "Alert: KubePodCrashLooping" in ctx
    assert "Namespace: monitoring" in ctx
    assert "Severity: critical" in ctx
    assert "Restarted 5 times in 10 minutes" in ctx


def test_format_fallback_message(sample_alert: Alert):
    service = AlertSummarizerService(llm_client=AsyncMock(), telegram_client=AsyncMock())
    msg = service.format_fallback_message(sample_alert)
    assert "🔴 <b>[FIRING] KubePodCrashLooping</b>" in msg
    assert "<code>monitoring</code>" in msg
    assert "Pod test-pod-123 is crash looping" in msg


def test_format_fallback_message_resolved(sample_resolved_alert: Alert):
    service = AlertSummarizerService(llm_client=AsyncMock(), telegram_client=AsyncMock())
    msg = service.format_fallback_message(sample_resolved_alert)
    assert "🟢 <b>[RESOLVED] KubePodCrashLooping</b>" in msg


@pytest.mark.asyncio
async def test_process_alert_with_llm_success(sample_alert: Alert):
    mock_llm = AsyncMock(spec=LLMClient)
    mock_llm.summarize_alert.return_value = (
        "• <b>Affected</b>: test-pod-123\n"
        "• <b>Cause</b>: OOMKilled\n"
        "• <b>Fix</b>: <code>kubectl logs test-pod-123</code>"
    )
    mock_tg = AsyncMock(spec=TelegramClient)
    mock_tg.send_message.return_value = True

    service = AlertSummarizerService(llm_client=mock_llm, telegram_client=mock_tg)
    success = await service.process_alert(sample_alert)

    assert success is True
    mock_llm.summarize_alert.assert_awaited_once()
    mock_tg.send_message.assert_awaited_once()
    sent_text = mock_tg.send_message.call_args[0][0]
    assert "OOMKilled" in sent_text
    assert "🔴 <b>[FIRING] KubePodCrashLooping</b>" in sent_text


@pytest.mark.asyncio
async def test_process_alert_with_llm_fallback(sample_alert: Alert):
    mock_llm = AsyncMock(spec=LLMClient)
    # Simulate LLM failure or timeout
    mock_llm.summarize_alert.return_value = None
    mock_tg = AsyncMock(spec=TelegramClient)
    mock_tg.send_message.return_value = True

    service = AlertSummarizerService(llm_client=mock_llm, telegram_client=mock_tg)
    success = await service.process_alert(sample_alert)

    assert success is True
    mock_tg.send_message.assert_awaited_once()
    sent_text = mock_tg.send_message.call_args[0][0]
    # Should use clean fallback template
    assert "Summary" in sent_text
    assert "Restarted 5 times in 10 minutes" in sent_text


@pytest.mark.asyncio
async def test_process_payload(sample_alert: Alert):
    mock_llm = AsyncMock(spec=LLMClient)
    mock_llm.summarize_alert.return_value = "• <b>AI Summary</b>"
    mock_tg = AsyncMock(spec=TelegramClient)
    mock_tg.send_message.return_value = True

    payload = AlertmanagerPayload(
        status="firing",
        alerts=[sample_alert, sample_alert],
    )

    service = AlertSummarizerService(llm_client=mock_llm, telegram_client=mock_tg)
    count = await service.process_payload(payload)

    assert count == 2
    assert mock_tg.send_message.await_count == 2
