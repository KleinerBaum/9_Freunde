from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any

REQUIRED_SERVICE_ACCOUNT_KEYS: tuple[str, ...] = (
    "type",
    "project_id",
    "private_key_id",
    "private_key",
    "client_email",
    "client_id",
    "token_uri",
)
DEFAULT_STAMMDATEN_SHEET_ID = "1ZuehceuiGnqpwhMxynfCulpSuCg0M2WE-nsQoTEJx-A"
DEFAULT_CHILDREN_TAB = "children"
REQUIRED_CHILDREN_COLUMNS = {"child_id", "name", "parent_email", "folder_id"}


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


def _require_str(mapping: dict[str, Any], key: str, path: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Fehlender oder leerer Key: {path}.{key}")
    return value.strip()


def _validate_secrets_schema(
    secrets: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], str, str, str]:
    service_account_info_raw = secrets.get("gcp_service_account")
    if not isinstance(service_account_info_raw, dict):
        raise ValueError("Bereich [gcp_service_account] fehlt oder ist ungültig.")

    gcp_raw = secrets.get("gcp")
    if not isinstance(gcp_raw, dict):
        raise ValueError("Bereich [gcp] fehlt oder ist ungültig.")

    for key in REQUIRED_SERVICE_ACCOUNT_KEYS:
        _require_str(service_account_info_raw, key, "gcp_service_account")

    _require_str(gcp_raw, "drive_contracts_folder_id", "gcp")
    _require_str(gcp_raw, "drive_photos_root_folder_id", "gcp")

    sheet_id_value = gcp_raw.get("stammdaten_sheet_id")
    spreadsheet_id = (
        str(sheet_id_value).strip()
        if isinstance(sheet_id_value, str) and str(sheet_id_value).strip()
        else DEFAULT_STAMMDATEN_SHEET_ID
    )

    children_tab_value = gcp_raw.get("children_tab")
    children_tab = (
        str(children_tab_value).strip()
        if isinstance(children_tab_value, str) and str(children_tab_value).strip()
        else DEFAULT_CHILDREN_TAB
    )

    calendar_id_value = gcp_raw.get("calendar_id")
    calendar_id = (
        str(calendar_id_value).strip()
        if isinstance(calendar_id_value, str) and str(calendar_id_value).strip()
        else ""
    )

    return service_account_info_raw, gcp_raw, spreadsheet_id, children_tab, calendar_id


def _drive_check(
    service_account_info: dict[str, Any], folder_id: str, folder_label: str
) -> None:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    drive_scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=drive_scopes,
    )
    drive = build("drive", "v3", credentials=creds)
    query = f"'{folder_id}' in parents and trashed = false"
    result = (
        drive.files()
        .list(
            q=query,
            pageSize=5,
            fields="files(id,name,mimeType)",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        )
        .execute()
    )
    file_count = len(result.get("files", []))
    _print_status(
        True,
        f"Drive list auf {folder_label} erfolgreich (Dateien gefunden: {file_count}).",
    )


def _quote_sheet_tab_for_a1(tab_name: str) -> str:
    escaped = tab_name.replace("'", "''")
    return f"'{escaped}'"


def _sheets_header_check(
    service_account_info: dict[str, Any], spreadsheet_id: str, children_tab: str
) -> None:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    sheets_scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=sheets_scopes,
    )
    sheets = build("sheets", "v4", credentials=creds)

    response = (
        sheets.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=f"{_quote_sheet_tab_for_a1(children_tab)}!1:1",
        )
        .execute()
    )
    values = response.get("values", [])
    if not values or not values[0]:
        raise ValueError(f"Sheet-Header {children_tab}!1:1 ist leer.")

    header = [str(column).strip() for column in values[0] if str(column).strip()]
    missing_columns = sorted(REQUIRED_CHILDREN_COLUMNS.difference(header))
    if missing_columns:
        raise ValueError(
            "Fehlende Pflichtspalten im children-Header: " + ", ".join(missing_columns)
        )

    _print_status(True, f"Sheets-Header gelesen ({len(header)} Spalten).")


def run(secrets_path: Path) -> int:
    try:
        secrets = _load_secrets(secrets_path)
        service_account_info, gcp, spreadsheet_id, children_tab, calendar_id = (
            _validate_secrets_schema(secrets)
        )
        _print_status(True, f"Secrets geladen aus {secrets_path}.")
        if calendar_id:
            _print_status(
                True,
                "Optionaler Key gcp.calendar_id gesetzt (Kalender-Checks möglich).",
            )
        else:
            _print_warning(
                "Optionaler Key gcp.calendar_id fehlt. In Google-Modus wird der Kalender-Check in der App fehlschlagen. "
                "Quick fix: Settings → Secrets → [gcp].calendar_id setzen."
            )
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        _print_status(False, f"Secrets-Check fehlgeschlagen: {error}")
        return 1

    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        _print_status(
            False,
            "Google API Python-Pakete fehlen. Bitte requirements.txt installieren.",
        )
        return 1

    try:
        _drive_check(
            service_account_info,
            str(gcp["drive_photos_root_folder_id"]).strip(),
            "Foto-Hauptordner",
        )
        _drive_check(
            service_account_info,
            str(gcp["drive_contracts_folder_id"]).strip(),
            "Vertragsordner",
        )
    except (HttpError, ValueError) as error:
        _print_status(False, f"Drive-Check fehlgeschlagen: {error}")
        return 1

    try:
        _sheets_header_check(service_account_info, spreadsheet_id, children_tab)
    except (HttpError, ValueError) as error:
        _print_status(False, f"Sheets-Check fehlgeschlagen: {error}")
        return 1

    _print_status(True, "Smoke-Check abgeschlossen.")
    _print_status(
        True,
        "UX-SMOKE: Wizard-Pfade dokumentiert (Step 1→4, Summary, DOCX/PDF/JSON/MD Export).",
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-Checks für Secrets, Google Drive (Contracts), Google Sheets (children header) und optionalen Hinweis zu gcp.calendar_id.",
    )
    parser.add_argument(
        "--secrets",
        type=Path,
        default=Path(".streamlit/secrets.toml"),
        help="Pfad zur Streamlit secrets.toml (Default: .streamlit/secrets.toml)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(run(args.secrets))
