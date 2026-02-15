from __future__ import annotations

import photo


def test_resolve_onedrive_folder_url_uses_configured_url(monkeypatch) -> None:
    monkeypatch.setattr(
        photo.st,
        "secrets",
        {"onedrive": {"shared_folder_url": "https://example.com/share"}},
    )

    resolved = photo._resolve_onedrive_folder_url()

    assert resolved == "https://example.com/share"


def test_resolve_onedrive_folder_url_uses_default_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(photo.st, "secrets", {})

    resolved = photo._resolve_onedrive_folder_url()

    assert resolved == photo.DEFAULT_ONEDRIVE_SHARED_FOLDER_URL
