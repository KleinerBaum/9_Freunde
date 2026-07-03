"""Update the 9_Freunde Google Sheet schema in place.

Run from the repo root in the devcontainer:

    source .venv/bin/activate
    python /mnt/data/update_9_freunde_google_sheet_schema.py --secrets .streamlit/secrets.toml

Behavior:
- Creates missing normalized tabs.
- Writes headers only when a tab is empty.
- Appends missing required columns to existing headers.
- Does not delete or reorder existing columns.
- Does not print secrets.
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

REQUIRED_COLUMNS_BY_SHEET: dict[str, list[str]] = {
    "children": [
        "child_id", "name", "parent_email", "folder_id", "download_consent",
        "birthdate", "start_date", "group", "primary_caregiver", "allergies",
        "notes_parent_visible", "notes_internal", "pickup_password", "status",
        "doctor_name", "doctor_phone", "health_insurance", "medication_regular",
        "dietary", "languages_at_home", "sleep_habits", "care_notes_optional",
    ],
    "parents": [
        "parent_id", "email", "name", "phone", "phone2", "address",
        "preferred_language", "emergency_contact_name", "emergency_contact_phone",
        "notifications_opt_in",
    ],
    "consents": [
        "consent_id", "child_id", "privacy_notice_ack", "excursions",
        "emergency_treatment", "whatsapp_group",
    ],
    "pickup_authorizations": [
        "pickup_id", "child_id", "name", "relationship", "phone",
        "valid_from", "valid_to", "active", "created_at", "created_by",
    ],
    "medications": [
        "med_id", "child_id", "date_time", "med_name", "dose", "given_by",
        "notes", "consent_doc_file_id", "created_at", "created_by",
    ],
    "content_pages": [
        "slug", "title_de", "title_en", "body_md_de", "body_md_en",
        "audience", "published", "updated_at",
    ],
}


def load_secrets(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise ValueError("secrets.toml did not parse to a mapping")
    return data


def require_section(secrets: dict[str, Any], name: str) -> dict[str, Any]:
    value = secrets.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"Missing or invalid [{name}] section")
    return value


def quote_tab(name: str) -> str:
    return "'" + name.replace("'", "''") + "'"


def configured_tab_name(gcp: dict[str, Any], logical_name: str) -> str:
    key = f"{logical_name}_tab"
    value = gcp.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return logical_name


def get_existing_tab_titles(service: Any, spreadsheet_id: str) -> set[str]:
    metadata = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="sheets(properties(title))",
    ).execute()
    return {
        str(sheet.get("properties", {}).get("title", "")).strip()
        for sheet in metadata.get("sheets", [])
        if str(sheet.get("properties", {}).get("title", "")).strip()
    }


def create_missing_tabs(service: Any, spreadsheet_id: str, tab_names: list[str]) -> None:
    existing = get_existing_tab_titles(service, spreadsheet_id)
    requests = [
        {"addSheet": {"properties": {"title": tab_name}}}
        for tab_name in tab_names
        if tab_name not in existing
    ]
    if not requests:
        return
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()
    for request in requests:
        print(f"CREATED tab: {request['addSheet']['properties']['title']}")


def read_header(service: Any, spreadsheet_id: str, tab_name: str) -> list[str]:
    response = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{quote_tab(tab_name)}!1:1",
    ).execute()
    values = response.get("values", [])
    if not values:
        return []
    return [str(cell).strip() for cell in values[0]]


def write_header(service: Any, spreadsheet_id: str, tab_name: str, header: list[str]) -> None:
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{quote_tab(tab_name)}!A1:ZZ1",
        valueInputOption="RAW",
        body={"values": [header]},
    ).execute()


def ensure_header(service: Any, spreadsheet_id: str, tab_name: str, required: list[str]) -> None:
    current = read_header(service, spreadsheet_id, tab_name)
    current_non_empty = [column for column in current if column]

    if not current_non_empty:
        write_header(service, spreadsheet_id, tab_name, required)
        print(f"WROTE   {tab_name}: {len(required)} columns")
        return

    updated = [*current_non_empty]
    missing = [column for column in required if column not in updated]
    if not missing:
        print(f"OK      {tab_name}: header already complete ({len(updated)} columns)")
        return

    updated.extend(missing)
    write_header(service, spreadsheet_id, tab_name, updated)
    print(f"UPDATED {tab_name}: appended {len(missing)} missing columns -> {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--secrets", type=Path, default=Path(".streamlit/secrets.toml"))
    args = parser.parse_args()

    try:
        secrets = load_secrets(args.secrets)
        gcp = require_section(secrets, "gcp")
        service_account_info = require_section(secrets, "gcp_service_account")
        spreadsheet_id = str(gcp.get("stammdaten_sheet_id", "")).strip()
        if not spreadsheet_id:
            raise ValueError("Missing gcp.stammdaten_sheet_id")

        credentials = service_account.Credentials.from_service_account_info(
            dict(service_account_info),
            scopes=SCOPES,
        )
        service = build("sheets", "v4", credentials=credentials)

        tab_map = {
            logical_name: configured_tab_name(gcp, logical_name)
            for logical_name in REQUIRED_COLUMNS_BY_SHEET
        }
        create_missing_tabs(service, spreadsheet_id, list(tab_map.values()))

        for logical_name, required in REQUIRED_COLUMNS_BY_SHEET.items():
            ensure_header(service, spreadsheet_id, tab_map[logical_name], required)

        print("DONE schema update")
        return 0
    except (HttpError, ValueError, OSError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
