from __future__ import annotations

from services import sheets_repo
import stammdaten


def test_sync_child_parent_email_uses_parent1_email() -> None:
    payload = {"parent_email": "old@example.com", "parent1__email": "new@example.com"}

    sheets_repo._sync_child_parent_email(payload)

    assert payload["parent_email"] == "new@example.com"


def test_derive_download_consent_prioritizes_denied() -> None:
    payload = {
        "download_consent": "unpixelated",
        "consent__photo_download_pixelated": "true",
        "consent__photo_download_unpixelated": "true",
        "consent__photo_download_denied": "true",
    }

    assert sheets_repo._derive_download_consent(payload) == "denied"


def test_derive_download_consent_uses_unpixelated_before_pixelated() -> None:
    payload = {
        "download_consent": "pixelated",
        "consent__photo_download_pixelated": "true",
        "consent__photo_download_unpixelated": "true",
        "consent__photo_download_denied": "false",
    }

    assert sheets_repo._derive_download_consent(payload) == "unpixelated"


def test_normalize_download_consent_accepts_denied() -> None:
    child = {"child_id": "abc", "download_consent": "DENIED"}

    normalized = stammdaten._normalize_child_record(child)

    assert normalized["download_consent"] == "denied"
