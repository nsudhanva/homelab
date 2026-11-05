from unittest.mock import MagicMock

import pytest

from gmail_classifier.gmail_client import GmailClient


def make_client(service: MagicMock) -> GmailClient:
    return GmailClient(
        client_id="cid",
        client_secret="csecret",
        refresh_token="rtoken",
        processed_label="ai-processed",
        service=service,
    )


def test_ensure_label_exists_when_present():
    mock_service = MagicMock()
    mock_labels_api = mock_service.users().labels()
    mock_labels_api.list.return_value.execute.return_value = {
        "labels": [
            {"id": "id-inbox", "name": "INBOX"},
            {"id": "id-proc", "name": "ai-processed"},
        ]
    }

    client = make_client(mock_service)
    assert client.get_user_labels() == {"INBOX": "id-inbox", "ai-processed": "id-proc"}
    assert client.ensure_label_exists("ai-processed") == "id-proc"
    mock_labels_api.create.assert_not_called()


def test_ensure_label_exists_creates_new():
    mock_service = MagicMock()
    mock_labels_api = mock_service.users().labels()
    mock_labels_api.list.return_value.execute.return_value = {"labels": []}
    mock_labels_api.create.return_value.execute.return_value = {
        "id": "new-label-id",
        "name": "ai-review",
    }

    lbl_id = make_client(mock_service).ensure_label_exists("ai-review")
    assert lbl_id == "new-label-id"
    mock_labels_api.create.assert_called_once_with(
        userId="me",
        body={
            "name": "ai-review",
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    )


@pytest.mark.parametrize(
    ("list_ids", "query", "extra", "expected"),
    [
        pytest.param(
            lambda c: c.list_messages_for_date("2026-09-16"),
            "after:2026/09/16 before:2026/09/17 -label:ai-processed",
            {},
            ["m-1", "m-2", "m-3"],
            id="date",
        ),
        pytest.param(
            lambda c: c.list_unprocessed_inbox_messages(),
            "-label:ai-processed in:inbox",
            {},
            ["m-1", "m-2", "m-3"],
            id="inbox",
        ),
        pytest.param(
            lambda c: c.list_messages_to_archive(older_than_days=90, quarantine_label="ai-review"),
            "in:inbox label:ai-processed -label:ai-review older_than:90d",
            {},
            ["m-1", "m-2", "m-3"],
            id="archive",
        ),
        pytest.param(
            lambda c: c.list_unread_messages(),
            "is:unread",
            {"maxResults": 500},
            ["m-1", "m-2", "m-3"],
            id="unread",
        ),
        pytest.param(
            lambda c: c.list_unread_messages(limit=2),
            "is:unread",
            {"maxResults": 500},
            ["m-1", "m-2"],
            id="unread-limit",
        ),
    ],
)
def test_list_methods_query_and_paginate(list_ids, query, extra, expected):
    mock_service = MagicMock()
    mock_messages_api = mock_service.users().messages()
    mock_messages_api.list.return_value.execute.side_effect = [
        {"messages": [{"id": "m-1"}, {"id": "m-2"}], "nextPageToken": "page-2"},
        {"messages": [{"id": "m-3"}]},
    ]

    assert list_ids(make_client(mock_service)) == expected
    calls = mock_messages_api.list.call_args_list
    assert calls[0].kwargs == {"userId": "me", "q": query, "pageToken": None, **extra}
    if len(expected) == 3:
        assert calls[1].kwargs["pageToken"] == "page-2"
    else:
        assert len(calls) == 1


def test_message_request_shapes():
    mock_service = MagicMock()
    mock_messages_api = mock_service.users().messages()
    client = make_client(mock_service)

    client.get_message_content("msg-999")
    mock_messages_api.get.assert_called_once_with(userId="me", id="msg-999", format="full")

    client.apply_label("msg-888", add_label_ids=["lbl-1", "lbl-2"])
    mock_messages_api.modify.assert_called_once_with(
        userId="me",
        id="msg-888",
        body={"addLabelIds": ["lbl-1", "lbl-2"]},
    )


def test_batch_archive_messages():
    mock_service = MagicMock()
    mock_messages_api = mock_service.users().messages()
    client = make_client(mock_service)

    assert client.batch_archive_messages([]) == 0
    mock_messages_api.batchModify.assert_not_called()

    assert client.batch_archive_messages(["msg-1", "msg-2"], batch_size=500) == 2
    mock_messages_api.batchModify.assert_called_once_with(
        userId="me",
        body={"ids": ["msg-1", "msg-2"], "removeLabelIds": ["INBOX"]},
    )


def test_batch_mark_read_chunks_requests():
    mock_service = MagicMock()
    mock_messages_api = mock_service.users().messages()
    client = make_client(mock_service)

    assert client.batch_mark_read([]) == 0
    assert client.batch_mark_read(["m-1", "m-2", "m-3"], batch_size=2) == 3
    mock_messages_api.batchModify.assert_any_call(
        userId="me", body={"ids": ["m-1", "m-2"], "removeLabelIds": ["UNREAD"]}
    )
    mock_messages_api.batchModify.assert_any_call(
        userId="me", body={"ids": ["m-3"], "removeLabelIds": ["UNREAD"]}
    )
