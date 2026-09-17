import base64
import html
import re
from typing import Any

from pydantic import BaseModel, Field

_SCRIPT_RE = re.compile(
    r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", re.IGNORECASE | re.DOTALL
)
_STYLE_RE = re.compile(r"<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>", re.IGNORECASE | re.DOTALL)
_BLOCK_TAG_RE = re.compile(
    r"</?(?:div|p|br|h[1-6]|li|tr|table|tbody|thead|blockquote|hr)[^>]*>",
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_NEWLINES_RE = re.compile(r"\n\s*\n")


class SanitizedEmail(BaseModel):
    id: str
    thread_id: str = Field(default="")
    subject: str = Field(default="(No Subject)")
    sender: str = Field(default="Unknown")
    date: str = Field(default="Unknown")
    snippet: str = Field(default="")
    body: str = Field(default="")


def decode_base64url(data: str) -> str:
    """Decode a base64url-encoded string with padding correction."""
    if not data:
        return ""
    # Normalize base64url padding
    padded = data + "=" * (-len(data) % 4)
    try:
        decoded_bytes = base64.urlsafe_b64decode(padded.encode("ascii"))
        return decoded_bytes.decode("utf-8", errors="replace")
    except Exception:
        return ""


def clean_html(raw_html: str) -> str:
    """Strip scripts, styles, HTML tags, unescape HTML entities, and normalize whitespace."""
    if not raw_html:
        return ""
    text = _SCRIPT_RE.sub(" ", raw_html)
    text = _STYLE_RE.sub(" ", text)
    text = _BLOCK_TAG_RE.sub("\n", text)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ").replace("\r", "")
    text = _WHITESPACE_RE.sub(" ", text)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)
    text = _NEWLINES_RE.sub("\n\n", text)
    return text.strip()


def extract_payload_text(payload: dict[str, Any]) -> tuple[str, str]:
    """Recursively traverse message payload parts to extract plain text and HTML content."""
    plain_parts: list[str] = []
    html_parts: list[str] = []

    mime_type = payload.get("mimeType", "").lower()
    body_data = payload.get("body", {}).get("data", "")
    if body_data:
        decoded = decode_base64url(body_data)
        if mime_type == "text/plain":
            plain_parts.append(decoded)
        elif mime_type == "text/html":
            html_parts.append(decoded)

    for part in payload.get("parts", []):
        sub_plain, sub_html = extract_payload_text(part)
        if sub_plain:
            plain_parts.append(sub_plain)
        if sub_html:
            html_parts.append(sub_html)

    return "\n".join(plain_parts).strip(), "\n".join(html_parts).strip()


def sanitize_message(msg: dict[str, Any], max_body_chars: int = 1500) -> SanitizedEmail:
    """Parse raw Gmail API message dictionary and produce a clean SanitizedEmail model."""
    msg_id = str(msg.get("id", ""))
    thread_id = str(msg.get("threadId", ""))
    snippet = str(msg.get("snippet", ""))

    payload = msg.get("payload", {})
    headers = payload.get("headers", [])

    subject = "(No Subject)"
    sender = "Unknown"
    date_str = "Unknown"

    for header in headers:
        name = header.get("name", "").lower()
        value = header.get("value", "")
        if name == "subject":
            subject = value or "(No Subject)"
        elif name == "from":
            sender = value or "Unknown"
        elif name == "date":
            date_str = value or "Unknown"

    plain_text, html_text = extract_payload_text(payload)

    if plain_text:
        body_content = clean_html(plain_text)
    elif html_text:
        body_content = clean_html(html_text)
    else:
        body_content = clean_html(snippet)

    # Truncate to first max_body_chars
    truncated_body = body_content[:max_body_chars].strip()

    return SanitizedEmail(
        id=msg_id,
        thread_id=thread_id,
        subject=subject,
        sender=sender,
        date=date_str,
        snippet=snippet,
        body=truncated_body,
    )
