from __future__ import annotations

import pytest

from tools.repair_photo_folders import (
    ChildRow,
    FolderValidation,
    classify_child_row,
    format_decision,
    parse_children_rows,
)


def _child_row(
    *,
    folder_id: str = "",
    legacy_folder_id: str = "",
    child_id: str = "child-123",
) -> ChildRow:
    return ChildRow(
        row_number=2,
        child_id=child_id,
        name="Sensitive Child Name",
        folder_id=folder_id,
        legacy_folder_id=legacy_folder_id,
    )


def test_parse_children_rows_requires_folder_id_header() -> None:
    values = [
        ["child_id", "name", "parent_email"],
        ["child-123", "Name", "p@example.org"],
    ]

    with pytest.raises(ValueError) as exc_info:
        parse_children_rows(values)

    assert "folder_id" in str(exc_info.value)


def test_parse_children_rows_reads_legacy_photo_folder_id_when_present() -> None:
    header, rows = parse_children_rows(
        [
            ["child_id", "name", "parent_email", "folder_id", "photo_folder_id"],
            ["child-123", "Name", "p@example.org", "", "legacy-folder"],
        ]
    )

    assert "folder_id" in header
    assert rows == [
        ChildRow(
            row_number=2,
            child_id="child-123",
            name="Name",
            folder_id="",
            legacy_folder_id="legacy-folder",
        )
    ]


def test_classify_valid_folder_id_is_ok() -> None:
    decision = classify_child_row(
        _child_row(folder_id="folder-123"),
        folder_validation=FolderValidation(True),
        legacy_validation=None,
    )

    assert decision.status == "OK"
    assert decision.action is None


def test_classify_missing_folder_id_with_valid_legacy_copies_legacy() -> None:
    decision = classify_child_row(
        _child_row(legacy_folder_id="legacy-folder"),
        folder_validation=None,
        legacy_validation=FolderValidation(True),
    )

    assert decision.status == "COPY_LEGACY"
    assert decision.action == "copy_legacy"


def test_classify_missing_folder_id_without_valid_legacy_creates_folder() -> None:
    decision = classify_child_row(
        _child_row(legacy_folder_id="legacy-folder"),
        folder_validation=None,
        legacy_validation=FolderValidation(False, "not_found"),
    )

    assert decision.status == "CREATE_FOLDER"
    assert decision.action == "create_folder"
    assert decision.reason == "not_found"


def test_classify_conflicting_folder_columns_does_not_overwrite() -> None:
    decision = classify_child_row(
        _child_row(folder_id="canonical-folder", legacy_folder_id="legacy-folder"),
        folder_validation=FolderValidation(True),
        legacy_validation=FolderValidation(True),
    )

    assert decision.status == "CONFLICT"
    assert decision.action is None


def test_classify_invalid_existing_folder_id_requires_manual_resolution() -> None:
    decision = classify_child_row(
        _child_row(folder_id="missing-folder"),
        folder_validation=FolderValidation(False, "not_found"),
        legacy_validation=None,
    )

    assert decision.status == "INVALID_FOLDER_ID"
    assert decision.action is None
    assert decision.reason == "not_found"


def test_format_decision_redacts_name_and_folder_ids() -> None:
    decision = classify_child_row(
        _child_row(folder_id="canonical-folder", legacy_folder_id="legacy-folder"),
        folder_validation=FolderValidation(True),
        legacy_validation=FolderValidation(True),
    )

    formatted = format_decision(decision)

    assert "row=2" in formatted
    assert "child_id=child-123" in formatted
    assert "Sensitive Child Name" not in formatted
    assert "canonical-folder" not in formatted
    assert "legacy-folder" not in formatted
