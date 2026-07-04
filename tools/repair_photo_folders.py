from __future__ import annotations

import argparse
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_STAMMDATEN_SHEET_ID = "1ZuehceuiGnqpwhMxynfCulpSuCg0M2WE-nsQoTEJx-A"
DEFAULT_CHILDREN_TAB = "children"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
REQUIRED_SERVICE_ACCOUNT_KEYS: tuple[str, ...] = (
    "type",
    "project_id",
    "private_key_id",
    "private_key",
    "client_email",
    "client_id",
    "token_uri",
)
REQUIRED_CHILDREN_COLUMNS: tuple[str, ...] = (
    "child_id",
    "name",
    "parent_email",
    "folder_id",
)
LEGACY_PHOTO_FOLDER_COLUMN = "photo_folder_id"


@dataclass(frozen=True, slots=True)
class RepairConfig:
    service_account_info: dict[str, Any]
    spreadsheet_id: str
    children_tab: str
    photos_root_folder_id: str


@dataclass(frozen=True, slots=True)
class ChildRow:
    row_number: int
    child_id: str
    name: str
    folder_id: str
    legacy_folder_id: str


@dataclass(frozen=True, slots=True)
class FolderValidation:
    valid: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class RepairDecision:
    status: str
    row_number: int
    child_id: str
    action: str | None = None
    reason: str = ""


def _print_status(ok: bool, message: str) -> None:
    prefix = "OK" if ok else "FAIL"
    print(f"[{prefix}] {message}")


def _print_warning(message: str) -> None:
    print(f"[WARN] {message}")


def _load_secrets(secrets_path: Path) -> dict[str, Any]:
    with secrets_path.open("rb") as file:
        data = tomllib.load(file)
    if not isinstance(data, dict):
        raise ValueError("Secrets-Datei ist kein gültiges TOML-Mapping.")
    return data


def _require_section(secrets: dict[str, Any], section: str) -> dict[str, Any]:
    value = secrets.get(section)
    if not isinstance(value, dict):
        raise ValueError(f"Bereich [{section}] fehlt oder ist ungültig.")
    return value


def _require_str(mapping: dict[str, Any], key: str, path: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Fehlender oder leerer Key: {path}.{key}")
    return value.strip()


def _optional_str(mapping: dict[str, Any], key: str, default: str) -> str:
    value = mapping.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def load_config(secrets_path: Path) -> RepairConfig:
    secrets = _load_secrets(secrets_path)
    service_account_info = _require_section(secrets, "gcp_service_account")
    gcp = _require_section(secrets, "gcp")

    for key in REQUIRED_SERVICE_ACCOUNT_KEYS:
        _require_str(service_account_info, key, "gcp_service_account")

    spreadsheet_id = _optional_str(
        gcp,
        "stammdaten_sheet_id",
        DEFAULT_STAMMDATEN_SHEET_ID,
    )
    children_tab = _optional_str(gcp, "children_tab", DEFAULT_CHILDREN_TAB)
    photos_root_folder_id = _require_str(gcp, "drive_photos_root_folder_id", "gcp")

    return RepairConfig(
        service_account_info=dict(service_account_info),
        spreadsheet_id=spreadsheet_id,
        children_tab=children_tab,
        photos_root_folder_id=photos_root_folder_id,
    )


def _quote_tab(name: str) -> str:
    return "'" + name.replace("'", "''") + "'"


def _column_letter(column_index: int) -> str:
    if column_index < 1:
        raise ValueError("column_index must be one-based.")

    letters = ""
    current = column_index
    while current:
        current, remainder = divmod(current - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _cell(row_number: int, column_index: int) -> str:
    return f"{_column_letter(column_index)}{row_number}"


def parse_children_rows(values: list[list[Any]]) -> tuple[list[str], list[ChildRow]]:
    if not values:
        raise ValueError("children-Tab enthält keine Header-Zeile.")

    header = [str(column).strip() for column in values[0]]
    missing = [column for column in REQUIRED_CHILDREN_COLUMNS if column not in header]
    if missing:
        raise ValueError(
            "Fehlende Pflichtspalten im children-Header: " + ", ".join(missing)
        )

    child_id_index = header.index("child_id")
    name_index = header.index("name")
    folder_id_index = header.index("folder_id")
    legacy_index = (
        header.index(LEGACY_PHOTO_FOLDER_COLUMN)
        if LEGACY_PHOTO_FOLDER_COLUMN in header
        else None
    )

    def cell(row: list[Any], index: int) -> str:
        if index >= len(row):
            return ""
        return str(row[index]).strip()

    rows: list[ChildRow] = []
    for row_number, row in enumerate(values[1:], start=2):
        if not any(str(value).strip() for value in row):
            continue
        rows.append(
            ChildRow(
                row_number=row_number,
                child_id=cell(row, child_id_index),
                name=cell(row, name_index),
                folder_id=cell(row, folder_id_index),
                legacy_folder_id=(
                    cell(row, legacy_index) if legacy_index is not None else ""
                ),
            )
        )
    return header, rows


def classify_child_row(
    child_row: ChildRow,
    *,
    folder_validation: FolderValidation | None,
    legacy_validation: FolderValidation | None,
) -> RepairDecision:
    child_id = child_row.child_id or "-"
    folder_id = child_row.folder_id.strip()
    legacy_folder_id = child_row.legacy_folder_id.strip()

    if folder_id and legacy_folder_id and folder_id != legacy_folder_id:
        return RepairDecision(
            status="CONFLICT",
            row_number=child_row.row_number,
            child_id=child_id,
            reason="folder_id and photo_folder_id differ; no automatic overwrite.",
        )

    if folder_id:
        if folder_validation is not None and folder_validation.valid:
            return RepairDecision(
                status="OK",
                row_number=child_row.row_number,
                child_id=child_id,
            )
        reason = folder_validation.reason if folder_validation is not None else "unknown"
        return RepairDecision(
            status="INVALID_FOLDER_ID",
            row_number=child_row.row_number,
            child_id=child_id,
            reason=reason,
        )

    if legacy_folder_id and legacy_validation is not None and legacy_validation.valid:
        return RepairDecision(
            status="COPY_LEGACY",
            row_number=child_row.row_number,
            child_id=child_id,
            action="copy_legacy",
        )

    return RepairDecision(
        status="CREATE_FOLDER",
        row_number=child_row.row_number,
        child_id=child_id,
        action="create_folder",
        reason=(
            legacy_validation.reason
            if legacy_folder_id and legacy_validation is not None
            else ""
        ),
    )


def format_decision(decision: RepairDecision, *, applied: bool = False) -> str:
    suffix = " applied" if applied else ""
    parts = [
        f"row={decision.row_number}",
        f"child_id={decision.child_id}",
        f"status={decision.status}{suffix}",
    ]
    if decision.action:
        parts.append(f"action={decision.action}")
    if decision.reason:
        parts.append(f"reason={decision.reason}")
    return " ".join(parts)


def _build_google_services(config: RepairConfig) -> tuple[Any, Any]:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    credentials = service_account.Credentials.from_service_account_info(
        config.service_account_info,
        scopes=scopes,
    )
    drive = build("drive", "v3", credentials=credentials)
    sheets = build("sheets", "v4", credentials=credentials)
    return drive, sheets


def _http_status(exc: Exception) -> int:
    response = getattr(exc, "resp", None)
    return int(getattr(response, "status", 0) or 0)


def validate_drive_folder(drive: Any, folder_id: str) -> FolderValidation:
    normalized_folder_id = folder_id.strip()
    if not normalized_folder_id:
        return FolderValidation(False, "missing")

    try:
        metadata = (
            drive.files()
            .get(
                fileId=normalized_folder_id,
                fields="id,mimeType,trashed,capabilities/canAddChildren",
                supportsAllDrives=True,
            )
            .execute()
        )
    except Exception as exc:
        status = _http_status(exc)
        if status == 403:
            return FolderValidation(False, "forbidden")
        if status == 404:
            return FolderValidation(False, "not_found")
        return FolderValidation(False, "api_error")

    if str(metadata.get("mimeType", "")).strip() != FOLDER_MIME_TYPE:
        return FolderValidation(False, "not_folder")
    if bool(metadata.get("trashed", False)):
        return FolderValidation(False, "trashed")

    capabilities = metadata.get("capabilities", {})
    if isinstance(capabilities, dict) and capabilities.get("canAddChildren") is False:
        return FolderValidation(False, "not_writable")

    return FolderValidation(True)


def _read_children_values(sheets: Any, config: RepairConfig) -> list[list[str]]:
    response = (
        sheets.spreadsheets()
        .values()
        .get(
            spreadsheetId=config.spreadsheet_id,
            range=f"{_quote_tab(config.children_tab)}!A:ZZ",
        )
        .execute()
    )
    values = response.get("values", [])
    if not isinstance(values, list):
        return []
    return [
        [str(cell) for cell in row]
        for row in values
        if isinstance(row, list)
    ]


def _update_folder_id_cell(
    sheets: Any,
    config: RepairConfig,
    *,
    row_number: int,
    folder_id_column_index: int,
    folder_id: str,
) -> None:
    cell = _cell(row_number, folder_id_column_index)
    (
        sheets.spreadsheets()
        .values()
        .update(
            spreadsheetId=config.spreadsheet_id,
            range=f"{_quote_tab(config.children_tab)}!{cell}",
            valueInputOption="RAW",
            body={"values": [[folder_id]]},
        )
        .execute()
    )


def _create_child_folder(drive: Any, config: RepairConfig, child_row: ChildRow) -> str:
    folder_name = child_row.name or child_row.child_id or f"child-{child_row.row_number}"
    metadata = {
        "name": folder_name,
        "mimeType": FOLDER_MIME_TYPE,
        "parents": [config.photos_root_folder_id],
    }
    created = (
        drive.files()
        .create(body=metadata, fields="id", supportsAllDrives=True)
        .execute()
    )
    return str(created.get("id", "")).strip()


def repair_photo_folders(config: RepairConfig, *, apply: bool) -> int:
    drive, sheets = _build_google_services(config)
    root_validation = validate_drive_folder(drive, config.photos_root_folder_id)
    if not root_validation.valid:
        _print_status(
            False,
            "Foto-Root-Ordner ist nicht gültig oder nicht beschreibbar. "
            f"reason={root_validation.reason}",
        )
        return 1

    values = _read_children_values(sheets, config)
    header, child_rows = parse_children_rows(values)
    folder_id_column_index = header.index("folder_id") + 1

    _print_status(
        True,
        f"children-Tab gelesen: {len(child_rows)} Kind-Datensätze.",
    )
    if not apply:
        _print_warning(
            "Dry-run aktiv: Es werden keine Ordner erstellt und keine Zellen geändert."
        )

    unresolved_count = 0
    changed_count = 0
    for child_row in child_rows:
        folder_validation = (
            validate_drive_folder(drive, child_row.folder_id)
            if child_row.folder_id
            else None
        )
        legacy_validation = (
            validate_drive_folder(drive, child_row.legacy_folder_id)
            if child_row.legacy_folder_id
            else None
        )
        decision = classify_child_row(
            child_row,
            folder_validation=folder_validation,
            legacy_validation=legacy_validation,
        )

        if decision.status in {"CONFLICT", "INVALID_FOLDER_ID"}:
            unresolved_count += 1
            _print_status(False, format_decision(decision))
            continue

        if not apply or decision.action is None:
            _print_status(True, format_decision(decision))
            continue

        if decision.action == "copy_legacy":
            _update_folder_id_cell(
                sheets,
                config,
                row_number=child_row.row_number,
                folder_id_column_index=folder_id_column_index,
                folder_id=child_row.legacy_folder_id,
            )
            changed_count += 1
            _print_status(True, format_decision(decision, applied=True))
            continue

        if decision.action == "create_folder":
            created_folder_id = _create_child_folder(drive, config, child_row)
            if not created_folder_id:
                unresolved_count += 1
                failed = RepairDecision(
                    status="CREATE_FAILED",
                    row_number=child_row.row_number,
                    child_id=child_row.child_id or "-",
                    reason="empty_file_id",
                )
                _print_status(False, format_decision(failed))
                continue
            _update_folder_id_cell(
                sheets,
                config,
                row_number=child_row.row_number,
                folder_id_column_index=folder_id_column_index,
                folder_id=created_folder_id,
            )
            changed_count += 1
            _print_status(True, format_decision(decision, applied=True))
            continue

        unresolved_count += 1
        _print_status(False, format_decision(decision))

    _print_status(
        unresolved_count == 0,
        f"Repair abgeschlossen. geändert={changed_count} unresolved={unresolved_count}",
    )
    return 0 if unresolved_count == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prüft und repariert children.folder_id für Foto-Uploads. "
            "Standard ist Dry-run; Schreibzugriffe benötigen --apply."
        )
    )
    parser.add_argument(
        "--secrets",
        type=Path,
        default=Path(".streamlit/secrets.toml"),
        help="Pfad zur Streamlit secrets.toml (Default: .streamlit/secrets.toml)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Erstellt fehlende Drive-Ordner und schreibt children.folder_id.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_config(args.secrets)
        return repair_photo_folders(config, apply=bool(args.apply))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as exc:
        _print_status(False, f"Konfigurationsfehler: {exc}")
        return 1
    except Exception as exc:
        _print_status(False, f"Repair fehlgeschlagen: {type(exc).__name__}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
