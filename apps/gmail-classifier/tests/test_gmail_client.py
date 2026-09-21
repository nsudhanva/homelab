from unittest.mock import MagicMock

from gmail_classifier.gmail_client import GmailClient


def test_get_user_labels():
    mock_service = MagicMock()
    mock_labels_api = mock_service.users().labels()
    mock_labels_api.list.return_value.execute.return_value = {
        "labels": [
            {"id": "id-inbox", "name": "INBOX"},
            {"id": "id-work", "name": "Work"},
            {"id": "id-finance", "name": "Finance"},
        ]
    }

    client = GmailClient(
        client_id="cid",
        client_secret="csecret",
        refresh_token="rtoken",
        service=mock_service,
    )
    labels = client.get_user_labels()
    assert labels == {
        "INBOX": "id-inbox",
        "Work": "id-work",
        "Finance": "id-finance",
    }


def test_ensure_label_exists_when_present():
    mock_service = MagicMock()
    mock_labels_api = mock_service.users().labels()
    mock_labels_api.list.return_value.execute.return_value = {
        "labels": [{"id": "id-proc", "name": "ai-processed"}]
    }

    client = GmailClient(
        client_id="cid",
        client_secret="csecret",
        refresh_token="rtoken",
        service=mock_service,
    )
    lbl_id = client.ensure_label_exists("ai-processed")
    assert lbl_id == "id-proc"
    mock_labels_api.create.assert_not_called()


def test_ensure_label_exists_creates_new():
    mock_service = MagicMock()
    mock_labels_api = mock_service.users().labels()
    mock_labels_api.list.return_value.execute.return_value = {"labels": []}
    mock_labels_api.create.return_value.execute.return_value = {
        "id": "new-label-id",
        "name": "ai-review",
    }

    client = GmailClient(
        client_id="cid",
        client_secret="csecret",
        refresh_token="rtoken",
        service=mock_service,
    )
    lbl_id = client.ensure_label_exists("ai-review")
    assert lbl_id == "new-label-id"
    mock_labels_api.create.assert_called_once_with(
        userId="me",
        body={
            "name": "ai-review",
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    )


def test_list_messages_for_date():
    mock_service = MagicMock()
    mock_messages_api = mock_service.users().messages()

    # Test pagination: first call returns page 1 with nextPageToken, second call returns page 2
    mock_messages_api.list.side_effect = [
        MagicMock(
            execute=MagicMock(
                return_value={
                    "messages": [{"id": "msg-1"}, {"id": "msg-2"}],
                    "nextPageToken": "token-page-2",
                }
            )
        ),
        MagicMock(
            execute=MagicMock(
                return_value={
                    "messages": [{"id": "msg-3"}],
                    "nextPageToken": None,
                }
            )
        ),
    ]

    client = GmailClient(
        client_id="cid",
        client_secret="csecret",
        refresh_token="rtoken",
        processed_label="ai-processed",
        service=mock_service,
    )

    msg_ids = client.list_messages_for_date("2026-09-16")
    assert msg_ids == ["msg-1", "msg-2", "msg-3"]
    assert mock_messages_api.list.call_count == 2
    # Verify query
    first_call_args = mock_messages_api.list.call_args_list[0]
    assert first_call_args.kwargs["q"] == "after:2026/09/16 before:2026/09/17 -label:ai-processed"


def test_get_message_content():
    mock_service = MagicMock()
    mock_messages_api = mock_service.users().messages()
    mock_messages_api.get.return_value.execute.return_value = {
        "id": "msg-999",
        "snippet": "Hello",
    }

    client = GmailClient(
        client_id="cid",
        client_secret="csecret",
        refresh_token="rtoken",
        service=mock_service,
    )
    content = client.get_message_content("msg-999")
    assert content["id"] == "msg-999"
    mock_messages_api.get.assert_called_once_with(
        userId="me",
        id="msg-999",
        format="full",
    )


def test_apply_label():
    mock_service = MagicMock()
    mock_messages_api = mock_service.users().messages()
    mock_messages_api.modify.return_value.execute.return_value = {"id": "msg-888"}

    client = GmailClient(
        client_id="cid",
        client_secret="csecret",
        refresh_token="rtoken",
        service=mock_service,
    )
    res = client.apply_label(
        "msg-888",
        add_label_ids=["lbl-1", "lbl-2"],
        remove_label_ids=["lbl-old"],
    )
    assert res["id"] == "msg-888"
    mock_messages_api.modify.assert_called_once_with(
        userId="me",
        id="msg-888",
        body={"addLabelIds": ["lbl-1", "lbl-2"], "removeLabelIds": ["lbl-old"]},
    )


def test_list_messages_to_archive():
    mock_service = MagicMock()
    mock_messages_api = mock_service.users().messages()
    mock_messages_api.list.return_value.execute.return_value = {
        "messages": [{"id": "arch-1"}, {"id": "arch-2"}],
        "nextPageToken": None,
    }

    client = GmailClient(
        client_id="cid",
        client_secret="csecret",
        refresh_token="rtoken",
        processed_label="ai-processed",
        service=mock_service,
    )
    res = client.list_messages_to_archive(older_than_days=90, quarantine_label="ai-review")
    assert res == ["arch-1", "arch-2"]
    mock_messages_api.list.assert_called_once_with(
        userId="me",
        q="in:inbox label:ai-processed -label:ai-review older_than:90d",
        pageToken=None,
    )


def test_batch_archive_messages():
    mock_service = MagicMock()
    mock_messages_api = mock_service.users().messages()

    client = GmailClient(
        client_id="cid",
        client_secret="csecret",
        refresh_token="rtoken",
        service=mock_service,
    )
    # Empty list should do nothing
    assert client.batch_archive_messages([]) == 0
    mock_messages_api.batchModify.assert_not_called()

    # With messages
    count = client.batch_archive_messages(["msg-1", "msg-2"], batch_size=500)
    assert count == 2
    mock_messages_api.batchModify.assert_called_once_with(
        userId="me",
        body={"ids": ["msg-1", "msg-2"], "removeLabelIds": ["INBOX"]},
    )
