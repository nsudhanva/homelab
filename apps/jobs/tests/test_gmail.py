import base64

from jobs.gmail import clean_body, parse_message


def b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_parse_message_reads_html_calendar_and_sent_label():
    raw = {
        "id": "m1",
        "internalDate": "1700000000000",
        "labelIds": ["SENT"],
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [
                {"name": "From", "value": '"Ann Lee" <Ann@Acme.com>'},
                {"name": "To", "value": "Me <me@example.com>, b@x.com"},
                {"name": "Subject", "value": "Interview"},
            ],
            "parts": [
                {"mimeType": "text/html", "body": {"data": b64("<p>Hi</p><style>x{}</style>")}},
                {
                    "mimeType": "text/calendar",
                    "body": {"data": b64("BEGIN:VEVENT\nSUMMARY:Onsite\nDTSTART:20231101\n")},
                },
                {"mimeType": "application/pdf", "filename": "resume.pdf", "body": {}},
            ],
        },
    }
    m = parse_message(raw)
    assert (m.sender_name, m.sender_email) == ("Ann Lee", "ann@acme.com")
    assert m.to == ["me@example.com", "b@x.com"]
    assert m.sent and m.attachments == ["resume.pdf"]
    assert "Calendar invite: SUMMARY:Onsite" in m.text and "Hi" in m.text and "x{}" not in m.text


def test_clean_body_drops_quoted_history_and_footers():
    body = "Thanks, see you Monday at 10am for the call.\n\nOn Tue, Ann wrote:\n> old text"
    assert clean_body(body) == "Thanks, see you Monday at 10am for the call."
    body = "Your application was sent to Acme for the role.\nPeople to follow\nBob Smith"
    assert clean_body(body) == "Your application was sent to Acme for the role."
