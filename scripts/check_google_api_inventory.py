from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import tomllib

from google.oauth2 import service_account
from googleapiclient.discovery import build


@dataclass(frozen=True)
class ApiInventoryEntry:
    name: str
    service_name: str
    status: str
    code_reference: str


INVENTORY: tuple[ApiInventoryEntry, ...] = (
    ApiInventoryEntry(
        name="Google Drive API",
        service_name="drive.googleapis.com",
        status="aktiv genutzt",
        code_reference="storage.py, services/drive_service.py, app.py",
    ),
    ApiInventoryEntry(
        name="Google Calendar API",
        service_name="calendar-json.googleapis.com",
        status="aktiv genutzt",
        code_reference="calendar.py, app.py",
    ),
    ApiInventoryEntry(
        name="Firestore API",
        service_name="firestore.googleapis.com",
        status="aktiv genutzt",
        code_reference="stammdaten.py, storage.py, scripts/check_firestore_prerequisites.py",
    ),
    ApiInventoryEntry(
        name="Google Sheets API",
        service_name="sheets.googleapis.com",
        status="optional/vorbereitet",
        code_reference="services/google_clients.py",
    ),
    ApiInventoryEntry(
        name="Google Docs API",
        service_name="docs.googleapis.com",
        status="aktuell ungenutzt",
        code_reference="keine Referenzen im Code",
    ),
    ApiInventoryEntry(
        name="Google Forms API",
        service_name="forms.googleapis.com",
        status="aktuell ungenutzt",
        code_reference="keine Referenzen im Code",
    ),
    ApiInventoryEntry(
        name="Google Tasks API",
        service_name="tasks.googleapis.com",
        status="aktuell ungenutzt",
        code_reference="keine Referenzen im Code",
    ),
)


def _load_secrets(secrets_path: Path) -> dict[str, Any]:
    with secrets_path.open("rb") as file:
        return tomllib.load(file)


def _build_client(
    *,
    service_account_info: dict[str, Any],
    scopes: list[str],
    service_name: str,
    version: str,
):
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=scopes,
    )
    return build(service_name, version, credentials=credentials)


def _run_check(
    name: str,
    required_key: str,
    optional_cfg: dict[str, Any],
    checker: Callable[[str], None],
) -> tuple[bool, str]:
    resource_id = optional_cfg.get(required_key)
    if not isinstance(resource_id, str) or not resource_id.strip():
        return (
            False,
            f"SKIP: `{required_key}` fehlt in `[gcp_optional_apis]` für {name}.",
        )

    try:
        checker(resource_id.strip())
        return True, "OK"
    except Exception as exc:  # pragma: no cover - external API
        return False, f"FAIL: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "API-Inventur ausgeben und optionale Minimal-Healthchecks "
            "für vorbereitete/ungeplante Google APIs ausführen."
        )
    )
    parser.add_argument(
        "--secrets",
        default=os.getenv("SECRETS_PATH", ".streamlit/secrets.toml"),
        help="Pfad zur secrets.toml (Default: .streamlit/secrets.toml)",
    )
    parser.add_argument(
        "--run-optional-healthchecks",
        action="store_true",
        help="Führt optional konfigurierte Healthchecks (Sheets/Docs/Forms/Tasks) aus.",
    )
    args = parser.parse_args()

    print("== Google API Inventur ==")
    for entry in INVENTORY:
        print(
            f"- {entry.name}: {entry.status} | service={entry.service_name} | code={entry.code_reference}"
        )

    if not args.run_optional_healthchecks:
        return 0

    secrets = _load_secrets(Path(args.secrets))
    sa_info = dict(secrets.get("gcp_service_account", {}))
    optional_cfg = dict(secrets.get("gcp_optional_apis", {}))

    if not sa_info:
        print("[FAIL] [gcp_service_account] fehlt in secrets.toml.")
        return 1

    print("\n== Optionale API-Healthchecks ==")

    sheets_client = _build_client(
        service_account_info=sa_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        service_name="sheets",
        version="v4",
    )
    ok, message = _run_check(
        "Sheets",
        "sheets_spreadsheet_id",
        optional_cfg,
        lambda spreadsheet_id: sheets_client.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, includeGridData=False)
        .execute(),
    )
    print(f"[{'OK' if ok else 'WARN'}] Sheets: {message}")

    docs_client = _build_client(
        service_account_info=sa_info,
        scopes=["https://www.googleapis.com/auth/documents.readonly"],
        service_name="docs",
        version="v1",
    )
    ok, message = _run_check(
        "Docs",
        "docs_document_id",
        optional_cfg,
        lambda document_id: docs_client.documents()
        .get(documentId=document_id)
        .execute(),
    )
    print(f"[{'OK' if ok else 'WARN'}] Docs: {message}")

    forms_client = _build_client(
        service_account_info=sa_info,
        scopes=["https://www.googleapis.com/auth/forms.body.readonly"],
        service_name="forms",
        version="v1",
    )
    ok, message = _run_check(
        "Forms",
        "forms_form_id",
        optional_cfg,
        lambda form_id: forms_client.forms().get(formId=form_id).execute(),
    )
    print(f"[{'OK' if ok else 'WARN'}] Forms: {message}")

    tasks_client = _build_client(
        service_account_info=sa_info,
        scopes=["https://www.googleapis.com/auth/tasks.readonly"],
        service_name="tasks",
        version="v1",
    )
    try:
        tasklist_result = tasks_client.tasklists().list(maxResults=1).execute()
        print(f"[OK] Tasks: {json.dumps(tasklist_result)[:120]}...")
    except Exception as exc:  # pragma: no cover - external API
        print(f"[WARN] Tasks: FAIL: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
