from bitwarden_organizer.items import render_folder_guide, summarize, untagged_items

from .conftest import FOLDERS, login_item


def test_summary_has_no_secrets() -> None:
    item = login_item("1", "Chase", "https://secure.chase.com/login")
    summary = summarize(item)
    text = summary.describe()
    assert summary.hosts == ("secure.chase.com",)
    assert summary.email_domain == "example.com"
    assert "chase.com" in text
    for secret in ("hunter2", "secret note", "1234", "me@"):
        assert secret not in text


def test_summary_handles_bare_hosts_and_cards() -> None:
    login = summarize(login_item("1", "x", "costco.com"))
    assert login.hosts == ("costco.com",)
    card = summarize({"id": "2", "type": 3, "name": "Visa", "card": {"brand": "Visa"}})
    assert card.kind == "card"
    assert card.card_brand == "Visa"
    assert card.hosts == ()


def test_untagged_skips_filed_and_deleted() -> None:
    items = [
        login_item("1", "a", "a.com"),
        login_item("2", "b", "b.com", folder_id="f-fin"),
        {**login_item("3", "c", "c.com"), "deletedDate": "2026-01-01T00:00:00Z"},
    ]
    assert [item["id"] for item in untagged_items(items)] == ["1"]


def test_folder_guide_lists_examples() -> None:
    items = [
        login_item("1", "chase.com", "chase.com", folder_id="f-fin"),
        login_item("2", "amex.com", "amex.com", folder_id="f-fin"),
        login_item("3", "loose", "loose.com"),
    ]
    guide = render_folder_guide(FOLDERS, items, examples_per_folder=1)
    assert "- Finance (2 items). Examples: chase.com [login]" in guide
    assert "amex.com" not in guide
    assert "- Shopping (0 items). Examples: no items yet" in guide
