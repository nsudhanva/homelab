import json

import httpx
import pytest

from gmail_classifier.classifier import EmailClassifier, extract_json_content
from gmail_classifier.sanitizer import SanitizedEmail


def test_extract_json_content():
    raw1 = '{"label": "Finance", "confidence": 0.95, "reason": "Bank statement"}'
    assert extract_json_content(raw1) == {
        "label": "Finance",
        "confidence": 0.95,
        "reason": "Bank statement",
    }

    raw2 = '```json\n{"label": "Work", "confidence": 0.88, "reason": "Meeting notice"}\n```'
    assert extract_json_content(raw2) == {
        "label": "Work",
        "confidence": 0.88,
        "reason": "Meeting notice",
    }

    raw3 = (
        'Here is the response:\n{"label": "Travel", "confidence": 0.9, "reason": "Flight"}\n'
        "Hope this helps!"
    )
    assert extract_json_content(raw3) == {
        "label": "Travel",
        "confidence": 0.9,
        "reason": "Flight",
    }


def test_filter_candidate_labels():
    classifier = EmailClassifier()
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
async def test_classify_success(monkeypatch):
    classifier = EmailClassifier(confidence_threshold=0.80)
    email = SanitizedEmail(
        id="1",
        subject="Quarterly Earnings Report",
        sender="ir@example.com",
        body="Q3 financial report and earnings call details.",
    )

    fake_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "label": "Finance",
                            "confidence": 0.95,
                            "reason": "Explicit quarterly earnings report and financial metrics.",
                        }
                    )
                }
            }
        ]
    }

    async def fake_post(self, url, **kwargs):
        return httpx.Response(200, json=fake_response, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await classifier.classify(email, ["Finance", "Personal", "Work"])
    assert result.label == "Finance"
    assert result.confidence == 0.95
    assert "Explicit quarterly earnings" in result.reason


@pytest.mark.asyncio
async def test_classify_low_confidence_fallback(monkeypatch):
    classifier = EmailClassifier(confidence_threshold=0.80, quarantine_label="ai-review")
    email = SanitizedEmail(
        id="2",
        subject="Random Note",
        sender="someone@example.com",
        body="Just checking in.",
    )

    fake_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "label": "Work",
                            "confidence": 0.65,
                            "reason": "Could be work related but vague.",
                        }
                    )
                }
            }
        ]
    }

    async def fake_post(self, url, **kwargs):
        return httpx.Response(200, json=fake_response, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await classifier.classify(email, ["Work", "Personal"])
    assert result.label == "ai-review"
    assert result.confidence == 0.65
    assert "Low confidence" in result.reason


@pytest.mark.asyncio
async def test_classify_unmatched_label_fallback(monkeypatch):
    classifier = EmailClassifier(confidence_threshold=0.80, quarantine_label="ai-review")
    email = SanitizedEmail(
        id="3",
        subject="Unknown topic",
        sender="info@example.com",
        body="Random newsletter.",
    )

    fake_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "label": "NonExistentLabel",
                            "confidence": 0.99,
                            "reason": "Found strange topic.",
                        }
                    )
                }
            }
        ]
    }

    async def fake_post(self, url, **kwargs):
        return httpx.Response(200, json=fake_response, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await classifier.classify(email, ["Work", "Personal"])
    assert result.label == "ai-review"
    assert "Unmatched label" in result.reason


def test_classify_sync_error_handling(monkeypatch):
    classifier = EmailClassifier(quarantine_label="ai-review")
    email = SanitizedEmail(
        id="4",
        subject="Timeout test",
        sender="server@example.com",
        body="Content",
    )

    def fake_post(self, url, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result = classifier.classify_sync(email, ["Work"])
    assert result.label == "ai-review"
    assert result.confidence == 0.0
    assert "Classifier error" in result.reason
