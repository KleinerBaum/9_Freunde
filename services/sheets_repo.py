from __future__ import annotations

from typing import Any
from uuid import uuid4

import streamlit as st

from config import get_app_config
from services.google_clients import get_sheets_client

CHILDREN_TAB = "children"
PARENTS_TAB = "parents"
CONSENTS_TAB = "consents"
DEFAULT_CACHE_TTL_SECONDS = 15
DEFAULT_DOWNLOAD_CONSENT = "pixelated"


class SheetsRepositoryError(RuntimeError):
    """Fehler beim Zugriff auf Google Sheets."""


def _sheet_id() -> str:
    app_config = get_app_config()
    if app_config.storage_mode != "google" or app_config.google is None:
        raise SheetsRepositoryError(
            "Google-Sheets-Zugriff ist nur im Google-Modus verfügbar."
        )
    return app_config.google.stammdaten_sheet_id


def _values_get(range_name: str) -> list[list[str]]:
    service = get_sheets_client()
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=_sheet_id(), range=range_name)
        .execute()
    )
    return response.get("values", [])


def _values_update(range_name: str, values: list[list[str]]) -> None:
    service = get_sheets_client()
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=_sheet_id(),
            range=range_name,
            valueInputOption="RAW",
            body={"values": values},
        )
        .execute()
    )


def _values_append(range_name: str, values: list[list[str]]) -> None:
    service = get_sheets_client()
    (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=_sheet_id(),
            range=range_name,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        )
        .execute()
    )


def _ensure_children_header_columns(required_columns: list[str]) -> list[str]:
    rows = _values_get(f"{CHILDREN_TAB}!A:ZZ")
    if not rows:
        header = ["child_id", "name", "parent_email", "folder_id", "photo_folder_id"]
        _values_update(f"{CHILDREN_TAB}!A1", [header])
        return header

    header = [str(col).strip() for col in rows[0]]
    changed = False
    for column in required_columns:
        if column not in header:
            header.append(column)
            changed = True

    if changed:
        _values_update(f"{CHILDREN_TAB}!A1:ZZ1", [header])

    return header


def _to_records(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []

    header = [str(col).strip() for col in rows[0]]
    records: list[dict[str, str]] = []
    for row in rows[1:]:
        if not any(cell for cell in row):
            continue
        record = {
            column: str(row[index]).strip() if index < len(row) else ""
            for index, column in enumerate(header)
            if column
        }
        records.append(record)
    return records


def _normalize_download_consent(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"pixelated", "unpixelated"}:
        return normalized
    return DEFAULT_DOWNLOAD_CONSENT


def _get_row_index_by_id(tab: str, id_field: str, value: str) -> tuple[int, list[str]]:
    rows = _values_get(f"{tab}!A:ZZ")
    if not rows:
        raise KeyError(f"Tab '{tab}' enthält keine Header-Zeile.")

    header = rows[0]
    try:
        id_col_index = header.index(id_field)
    except ValueError as exc:
        raise KeyError(f"Spalte '{id_field}' fehlt in Tab '{tab}'.") from exc

    for row_offset, row in enumerate(rows[1:], start=2):
        current_value = (
            str(row[id_col_index]).strip() if id_col_index < len(row) else ""
        )
        if current_value == value:
            return row_offset, header

    raise KeyError(f"Eintrag mit {id_field}='{value}' nicht gefunden.")


@st.cache_data(ttl=DEFAULT_CACHE_TTL_SECONDS, show_spinner=False)
def get_children() -> list[dict[str, str]]:
    _ensure_children_header_columns(
        ["folder_id", "photo_folder_id", "download_consent"]
    )
    rows = _values_get(f"{CHILDREN_TAB}!A:ZZ")
    children = _to_records(rows)
    for child in children:
        child["download_consent"] = _normalize_download_consent(
            child.get("download_consent")
        )
    return sorted(children, key=lambda item: item.get("name", ""))


@st.cache_data(ttl=DEFAULT_CACHE_TTL_SECONDS, show_spinner=False)
def get_child_by_parent_email(email: str) -> dict[str, str] | None:
    normalized_email = email.strip().lower()
    for child in get_children():
        if child.get("parent_email", "").strip().lower() == normalized_email:
            return child
    return None


@st.cache_data(ttl=DEFAULT_CACHE_TTL_SECONDS, show_spinner=False)
def get_child_by_id(child_id: str) -> dict[str, str] | None:
    normalized_child_id = child_id.strip()
    for child in get_children():
        if child.get("child_id", "").strip() == normalized_child_id:
            return child
    return None


def add_child(child_dict: dict[str, Any]) -> str:
    child_id = uuid4().hex
    payload = {
        **child_dict,
        "child_id": child_id,
        "download_consent": _normalize_download_consent(
            str(child_dict.get("download_consent", ""))
        ),
    }

    header = _ensure_children_header_columns(
        ["folder_id", "photo_folder_id", "download_consent"]
    )

    row_values = [str(payload.get(column, "")).strip() for column in header]
    _values_append(f"{CHILDREN_TAB}!A:ZZ", [row_values])

    get_children.clear()
    get_child_by_parent_email.clear()
    get_child_by_id.clear()
    return child_id


def update_child(child_id: str, patch_dict: dict[str, Any]) -> None:
    _ensure_children_header_columns(
        ["folder_id", "photo_folder_id", "download_consent"]
    )
    row_index, header = _get_row_index_by_id(CHILDREN_TAB, "child_id", child_id)

    existing_rows = _values_get(f"{CHILDREN_TAB}!A{row_index}:ZZ{row_index}")
    existing_row = existing_rows[0] if existing_rows else []

    current_payload = {
        column: str(existing_row[index]).strip() if index < len(existing_row) else ""
        for index, column in enumerate(header)
    }
    current_payload.update(
        {key: str(value).strip() for key, value in patch_dict.items()}
    )
    current_payload["download_consent"] = _normalize_download_consent(
        current_payload.get("download_consent")
    )

    row_values = [current_payload.get(column, "") for column in header]
    _values_update(f"{CHILDREN_TAB}!A{row_index}:ZZ{row_index}", [row_values])

    get_children.clear()
    get_child_by_parent_email.clear()
    get_child_by_id.clear()


@st.cache_data(ttl=DEFAULT_CACHE_TTL_SECONDS, show_spinner=False)
def get_parents() -> list[dict[str, str]]:
    rows = _values_get(f"{PARENTS_TAB}!A:ZZ")
    return _to_records(rows)


def add_parent(parent_dict: dict[str, Any]) -> str:
    parent_id = str(parent_dict.get("parent_id") or uuid4().hex)
    payload = {**parent_dict, "parent_id": parent_id}

    rows = _values_get(f"{PARENTS_TAB}!A:ZZ")
    if not rows:
        header = ["parent_id", "email", "name", "phone"]
        _values_update(f"{PARENTS_TAB}!A1", [header])
    else:
        header = [str(col).strip() for col in rows[0]]

    row_values = [str(payload.get(column, "")).strip() for column in header]
    _values_append(f"{PARENTS_TAB}!A:ZZ", [row_values])

    get_parents.clear()
    return parent_id


def update_parent(parent_id: str, patch_dict: dict[str, Any]) -> None:
    row_index, header = _get_row_index_by_id(PARENTS_TAB, "parent_id", parent_id)

    existing_rows = _values_get(f"{PARENTS_TAB}!A{row_index}:ZZ{row_index}")
    existing_row = existing_rows[0] if existing_rows else []

    current_payload = {
        column: str(existing_row[index]).strip() if index < len(existing_row) else ""
        for index, column in enumerate(header)
    }
    current_payload.update(
        {key: str(value).strip() for key, value in patch_dict.items()}
    )

    row_values = [current_payload.get(column, "") for column in header]
    _values_update(f"{PARENTS_TAB}!A{row_index}:ZZ{row_index}", [row_values])

    get_parents.clear()
