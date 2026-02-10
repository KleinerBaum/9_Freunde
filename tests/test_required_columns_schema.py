from __future__ import annotations

from services import local_ods_repo, sheets_repo


def test_required_columns_by_sheet_matches_google_schema() -> None:
    assert (
        local_ods_repo.REQUIRED_COLUMNS_BY_SHEET
        == sheets_repo.REQUIRED_COLUMNS_BY_SHEET
    )


def test_consents_schema_v1_required_columns_supported() -> None:
    assert sheets_repo.CONSENTS_REQUIRED_COLUMNS == [
        "consent_id",
        "child_id",
        "privacy_notice_ack",
        "excursions",
        "emergency_treatment",
        "whatsapp_group",
        "photo_download",
    ]
