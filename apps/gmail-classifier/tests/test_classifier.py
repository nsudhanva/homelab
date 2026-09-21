from unittest.mock import AsyncMock, MagicMock

import pytest

from gmail_classifier.classifier import ClassificationResult, EmailClassifier, LLMConnectionError
from gmail_classifier.sanitizer import SanitizedEmail


def test_filter_candidate_labels():
    classifier = EmailClassifier(agent=MagicMock())
    labels = {
        "INBOX": "id1",
        "UNREAD": "id2",
        "SPAM": "id3",
        "CATEGORY_PROMOTIONS": "id4",
        "ai-processed": "id5",
        "ai-review": "id6",
        "Personal": "id7",
        "Work": "id8",
        "Finance": "id9",
    }
    curated = classifier.filter_candidate_labels(labels)
    assert curated == ["Finance", "Personal", "Work"]


@pytest.mark.asyncio
async def test_classify_success():
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(
        return_value=MagicMock(
            output=ClassificationResult(
                label="Finance",
                confidence=0.95,
                reason="Explicit quarterly earnings report and financial metrics.",
            )
        )
    )
    classifier = EmailClassifier(confidence_threshold=0.80, agent=mock_agent)
    email = SanitizedEmail(
        id="1",
        subject="Quarterly Earnings Report",
        sender="ir@example.com",
        body="Q3 financial report and earnings call details.",
    )

    result = await classifier.classify(email, ["Finance", "Personal", "Work"])
    assert result.label == "Finance"
    assert result.confidence == 0.95
    assert "Explicit quarterly earnings" in result.reason
    mock_agent.run.assert_called_once()


@pytest.mark.asyncio
async def test_classify_low_confidence_fallback():
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(
        return_value=MagicMock(
            output=ClassificationResult(
                label="Work",
                confidence=0.65,
                reason="Could be work related but vague.",
            )
        )
    )
    classifier = EmailClassifier(
        confidence_threshold=0.80, quarantine_label="ai-review", agent=mock_agent
    )
    email = SanitizedEmail(
        id="2",
        subject="Random Note",
        sender="someone@example.com",
        body="Just checking in.",
    )

    result = await classifier.classify(email, ["Work", "Personal"])
    assert result.label == "ai-review"
    assert result.confidence == 0.65
    assert "Low confidence" in result.reason


@pytest.mark.asyncio
async def test_classify_unmatched_label_fallback():
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(
        return_value=MagicMock(
            output=ClassificationResult(
                label="NonExistentLabel",
                confidence=0.99,
                reason="Found strange topic.",
            )
        )
    )
    classifier = EmailClassifier(
        confidence_threshold=0.80,
        quarantine_label="ai-review",
        allow_label_creation=False,
        agent=mock_agent,
    )
    email = SanitizedEmail(
        id="3",
        subject="Unknown topic",
        sender="info@example.com",
        body="Random newsletter.",
    )

    result = await classifier.classify(email, ["Work", "Personal"])
    assert result.label == "ai-review"
    assert "Unmatched label" in result.reason


@pytest.mark.asyncio
async def test_classify_autonomous_label_creation():
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(
        return_value=MagicMock(
            output=ClassificationResult(
                label="Newsletters",
                confidence=0.95,
                reason="Digest of news articles.",
            )
        )
    )
    classifier = EmailClassifier(
        confidence_threshold=0.80,
        quarantine_label="ai-review",
        allow_label_creation=True,
        agent=mock_agent,
    )
    email = SanitizedEmail(
        id="3b",
        subject="Daily Tech Digest",
        sender="digest@example.com",
        body="Here is your tech newsletter.",
    )

    result = await classifier.classify(email, ["Work", "Personal"])
    assert result.label == "Newsletters"
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_classify_explicit_quarantine():
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(
        return_value=MagicMock(
            output=ClassificationResult(
                label="QUARANTINE",
                confidence=0.95,
                reason="Phishing attempt detected.",
            )
        )
    )
    classifier = EmailClassifier(
        confidence_threshold=0.80,
        quarantine_label="ai-review",
        allow_label_creation=True,
        agent=mock_agent,
    )
    email = SanitizedEmail(
        id="3c",
        subject="Suspicious link",
        sender="phish@example.com",
        body="Click here now.",
    )

    result = await classifier.classify(email, ["Work", "Personal"])
    assert result.label == "ai-review"
    assert "Quarantined" in result.reason


def test_classify_sync_llm_connection_error():
    mock_agent = MagicMock()
    mock_agent.run_sync.side_effect = RuntimeError("Connection timeout")
    classifier = EmailClassifier(quarantine_label="ai-review", agent=mock_agent)
    email = SanitizedEmail(
        id="4",
        subject="Timeout test",
        sender="server@example.com",
        body="Content",
    )

    with pytest.raises(LLMConnectionError):
        classifier.classify_sync(email, ["Work"])


def test_classify_sync_error_handling():
    mock_agent = MagicMock()
    mock_agent.run_sync.side_effect = ValueError("Malformed model structure")
    classifier = EmailClassifier(quarantine_label="ai-review", agent=mock_agent)
    email = SanitizedEmail(
        id="4",
        subject="Error test",
        sender="server@example.com",
        body="Content",
    )

    result = classifier.classify_sync(email, ["Work"])
    assert result.label == "ai-review"
    assert result.confidence == 0.0
    assert "Model output error" in result.reason


def test_classify_no_curated_labels():
    mock_agent = MagicMock()
    classifier = EmailClassifier(
        quarantine_label="ai-review",
        allow_label_creation=False,
        agent=mock_agent,
    )
    email = SanitizedEmail(id="5", subject="Empty", body="Empty")

    result = classifier.classify_sync(email, ["INBOX", "SPAM"])
    assert result.label == "ai-review"
    assert "No active curated user labels available" in result.reason
    mock_agent.run_sync.assert_not_called()


def test_classify_no_curated_labels_with_creation_enabled():
    mock_agent = MagicMock()
    mock_agent.run_sync.return_value = MagicMock(
        output=ClassificationResult(
            label="Newsletters",
            confidence=0.92,
            reason="Digest newsletter.",
        )
    )
    classifier = EmailClassifier(
        quarantine_label="ai-review",
        allow_label_creation=True,
        agent=mock_agent,
    )
    email = SanitizedEmail(id="5b", subject="Digest", body="Latest updates")

    result = classifier.classify_sync(email, ["INBOX", "SPAM"])
    assert result.label == "Newsletters"
    assert result.confidence == 0.92
    mock_agent.run_sync.assert_called_once()
