from drive_organizer.inspector import FileInspector


def test_inspect_plain_text():
    content = b"This is a test document with some words and lines."
    res = FileInspector.inspect_bytes("test.txt", "text/plain", content)
    assert res.is_media is False
    assert res.has_extractable_text is True
    assert "test document" in res.extracted_text


def test_inspect_media_image():
    # Simple 1x1 image bytes or empty bytes with image mime
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    res = FileInspector.inspect_bytes(
        "photo.png",
        "image/png",
        fake_png,
        created_time_str="2026-08-15T10:00:00Z",
    )
    assert res.is_media is True
    assert res.media_date is not None
    assert res.media_date.year == 2026
    assert res.media_date.month == 8
