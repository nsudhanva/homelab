import base64

from gmail_classifier.sanitizer import (
    clean_html,
    decode_base64url,
    sanitize_message,
)


def test_decode_base64url():
    raw = "Hello World! Special characters: & < > €"
    encoded = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")
    decoded = decode_base64url(encoded)
    assert decoded == raw


def test_clean_html():
    raw_html = """
    <html>
      <head>
        <style>body { color: red; }</style>
        <script>alert('malicious');</script>
      </head>
      <body>
        <h1>Order Confirmation</h1>
        <p>Your item &amp; invoice are ready.&nbsp;&nbsp;Thank you!</p>
      </body>
    </html>
    """
    cleaned = clean_html(raw_html)
    assert "body { color: red; }" not in cleaned
    assert "alert('malicious');" not in cleaned
    assert "Order Confirmation" in cleaned
    assert "Your item & invoice are ready. Thank you!" in cleaned


def test_sanitize_message_plain_text():
    content = "This is a plain text email body."
    b64 = base64.urlsafe_b64encode(content.encode("utf-8")).decode("ascii")

    raw_msg = {
        "id": "msg-101",
        "threadId": "th-202",
        "snippet": "Short snippet",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": "Server Alert: Disk Full"},
                {"name": "From", "value": "alerts@infra.example.com"},
                {"name": "Date", "value": "Thu, 17 Sep 2026 12:00:00 GMT"},
            ],
            "body": {"data": b64},
        },
    }

    email = sanitize_message(raw_msg)
    assert email.id == "msg-101"
    assert email.thread_id == "th-202"
    assert email.subject == "Server Alert: Disk Full"
    assert email.sender == "alerts@infra.example.com"
    assert email.date == "Thu, 17 Sep 2026 12:00:00 GMT"
    assert email.body == "This is a plain text email body."


def test_sanitize_message_multipart_with_html():
    html_content = "<p>Please review your <b>monthly statement</b>.</p>"
    b64_html = base64.urlsafe_b64encode(html_content.encode("utf-8")).decode("ascii")

    raw_msg = {
        "id": "msg-102",
        "threadId": "th-203",
        "snippet": "Statement",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "Subject", "value": "Monthly Statement"},
                {"name": "From", "value": "billing@bank.example.com"},
            ],
            "parts": [
                {
                    "mimeType": "text/html",
                    "body": {"data": b64_html},
                }
            ],
        },
    }

    email = sanitize_message(raw_msg)
    assert email.id == "msg-102"
    assert email.subject == "Monthly Statement"
    assert email.sender == "billing@bank.example.com"
    assert email.body == "Please review your monthly statement."


def test_sanitize_message_truncation():
    long_content = "Word " * 500  # 2500 chars
    b64 = base64.urlsafe_b64encode(long_content.encode("utf-8")).decode("ascii")

    raw_msg = {
        "id": "msg-103",
        "payload": {
            "mimeType": "text/plain",
            "headers": [],
            "body": {"data": b64},
        },
    }

    email = sanitize_message(raw_msg, max_body_chars=1500)
    assert len(email.body) <= 1500
    assert email.subject == "(No Subject)"
    assert email.sender == "Unknown"
