from __future__ import annotations

from typing import Any
from uuid import uuid4

import streamlit as st
from googleapiclient.errors import HttpError

from config import GoogleConfig, get_app_config
from services.google_clients import get_sheets_client

DEFAULT_CACHE_TTL_SECONDS = 15
DEFAULT_DOWNLOAD_CONSENT = "pixelated"
CHILDREN_REQUIRED_COLUMNS = [
    "child_id",
    "name",
    "parent_email",
    "folder_id",
    "photo_folder_id",
    "download_consent",
    "birthdate",
    "start_date",
    "group",
    "primary_caregiver",
    "allergies",
    "notes_parent_visible",
    "notes_internal",
    "pickup_password",
    "status",
    "doctor_name",
    "doctor_phone",
    "health_insurance",
    "medication_regular",
    "dietary",
    "languages_at_home",
    "sleep_habits",
    "care_notes_optional",
]
PARENTS_REQUIRED_COLUMNS = [
    "parent_id",
    "email",
    "name",
    "phone",
    "phone2",
    "address",
    "preferred_language",
    "emergency_contact_name",
    "emergency_contact_phone",
    "notifications_opt_in",
]


PICKUP_AUTHORIZATIONS_REQUIRED_COLUMNS = [
    "pickup_id",
    "child_id",
    "name",
    "relationship",
    "phone",
    "valid_from",
    "valid_to",
    "active",
    "created_at",
    "created_by",
]


MEDICATIONS_REQUIRED_COLUMNS = [
    "med_id",
    "child_id",
    "date_time",
    "med_name",
    "dose",
    "given_by",
    "notes",
    "consent_doc_file_id",
    "created_at",
    "created_by",
]

PHOTO_META_REQUIRED_COLUMNS = [
    "file_id",
    "child_id",
    "album",
    "status",
    "uploaded_at",
    "uploaded_by",
    "retention_until",
]


class SheetsRepositoryError(RuntimeError):
    """Fehler beim Zugriff auf Google Sheets."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _http_error_message(exc: HttpError) -> str:
    details = getattr(exc, "error_details", None)
    if isinstance(details, list) and details:
        message = details[0].get("message")
        if isinstance(message, str):
            return message

    content = getattr(exc, "content", b"")
    if isinstance(content, bytes):
        decoded_content = content.decode("utf-8", errors="ignore")
        if decoded_content:
            return decoded_content

    return str(exc)


def _is_missing_sheet_range_error(exc: HttpError) -> bool:
    status = getattr(exc.resp, "status", None)
    if status != 400:
        return False

    error_message = _http_error_message(exc).lower()
    return "unable to parse range" in error_message


def _translate_http_error(exc: HttpError) -> SheetsRepositoryError:
    status = getattr(exc.resp, "status", None)
    error_message = _http_error_message(exc)

    if _is_missing_sheet_range_error(exc):
        return SheetsRepositoryError(
            "Tabellenblatt/Range nicht gefunden (400: Unable to parse range). "
            "Bitte 'gcp.pickup_authorizations_tab' prüfen oder den Tab im "
            "Stammdaten-Sheet anlegen. / Sheet/tab name not found (400: Unable "
            "to parse range). Check 'gcp.pickup_authorizations_tab' or create "
            "the tab in the master-data spreadsheet.",
            status_code=status,
        )

    if status == 403:
        return SheetsRepositoryError(
            "Kein Zugriff auf das Stammdaten-Sheet (403). Bitte den Service-Account "
            "für die Tabelle 'gcp.stammdaten_sheet_id' berechtigen. / "
            "Access denied to the master-data sheet (403). Please grant the service "
            "account access to the sheet configured in 'gcp.stammdaten_sheet_id'.",
            status_code=status,
        )

    if status == 404:
        return SheetsRepositoryError(
            "Google-Sheet nicht gefunden (404). Bitte die konfigurierte "
            "'gcp.stammdaten_sheet_id' prüfen. / Google spreadsheet not found "
            "(404). Verify the configured 'gcp.stammdaten_sheet_id'.",
            status_code=status,
        )

    return SheetsRepositoryError(
        "Google-Sheets-Anfrage fehlgeschlagen. Bitte Konfiguration und Berechtigungen "
        "prüfen. / Google Sheets request failed. Please verify configuration and "
        f"permissions. Details: {error_message}",
        status_code=status,
    )


def _sheet_id() -> str:
    app_config = get_app_config()
    if app_config.storage_mode != "google" or app_config.google is None:
        raise SheetsRepositoryError(
            "Google-Sheets-Zugriff ist nur im Google-Modus verfügbar."
        )
    return app_config.google.stammdaten_sheet_id


def _google_config() -> GoogleConfig:
    app_config = get_app_config()
    if app_config.storage_mode != "google" or app_config.google is None:
        raise SheetsRepositoryError(
            "Google-Sheets-Zugriff ist nur im Google-Modus verfügbar."
        )
    return app_config.google


def _children_tab() -> str:
    return _google_config().children_tab


def _parents_tab() -> str:
    return _google_config().parents_tab


def _consents_tab() -> str:
    return _google_config().consents_tab


def _pickup_authorizations_tab() -> str:
    return _google_config().pickup_authorizations_tab


def _medications_tab() -> str:
    return _google_config().medications_tab


def _photo_meta_tab() -> str:
    return _google_config().photo_meta_tab


def _values_get(range_name: str) -> list[list[str]]:
    service = get_sheets_client()
    try:
        response = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=_sheet_id(), range=range_name)
            .execute()
        )
    except HttpError as exc:
        raise _translate_http_error(exc) from exc
    return response.get("values", [])


def _values_update(range_name: str, values: list[list[str]]) -> None:
    service = get_sheets_client()
    try:
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
    except HttpError as exc:
        raise _translate_http_error(exc) from exc


def _values_append(range_name: str, values: list[list[str]]) -> None:
    service = get_sheets_client()
    try:
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
    except HttpError as exc:
        raise _translate_http_error(exc) from exc


def _get_tab_sheet_id(tab_name: str) -> int:
    service = get_sheets_client()
    try:
        response = (
            service.spreadsheets()
            .get(
                spreadsheetId=_sheet_id(),
                fields="sheets(properties(sheetId,title))",
            )
            .execute()
        )
    except HttpError as exc:
        raise _translate_http_error(exc) from exc

    for sheet in response.get("sheets", []):
        properties = sheet.get("properties", {})
        if str(properties.get("title", "")).strip() == tab_name:
            sheet_id = properties.get("sheetId")
            if isinstance(sheet_id, int):
                return sheet_id

    raise KeyError(f"Tab '{tab_name}' nicht gefunden.")


def _delete_row(tab: str, row_index: int) -> None:
    if row_index < 2:
        raise ValueError("Header-Zeile kann nicht gelöscht werden.")

    service = get_sheets_client()
    sheet_id = _get_tab_sheet_id(tab)
    try:
        (
            service.spreadsheets()
            .batchUpdate(
                spreadsheetId=_sheet_id(),
                body={
                    "requests": [
                        {
                            "deleteDimension": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "dimension": "ROWS",
                                    "startIndex": row_index - 1,
                                    "endIndex": row_index,
                                }
                            }
                        }
                    ]
                },
            )
            .execute()
        )
    except HttpError as exc:
        raise _translate_http_error(exc) from exc


def _create_sheet_if_missing(tab_name: str) -> None:
    service = get_sheets_client()
    try:
        (
            service.spreadsheets()
            .batchUpdate(
                spreadsheetId=_sheet_id(),
                body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
            )
            .execute()
        )
    except HttpError as exc:
        if "already exists" in _http_error_message(exc).lower():
            return
        raise _translate_http_error(exc) from exc


def _ensure_children_header_columns(required_columns: list[str]) -> list[str]:
    rows = _values_get(f"{_children_tab()}!A:ZZ")
    if not rows:
        header = ["child_id", "name", "parent_email", "folder_id", "photo_folder_id"]
        _values_update(f"{_children_tab()}!A1", [header])
        rows = [[*header]]

    header = [str(col).strip() for col in rows[0]]
    changed = False
    for column in required_columns:
        if column not in header:
            header.append(column)
            changed = True

    if changed:
        _values_update(f"{_children_tab()}!A1:ZZ1", [header])

    return header


def _ensure_parents_header_columns(required_columns: list[str]) -> list[str]:
    rows = _values_get(f"{_parents_tab()}!A:ZZ")
    if not rows:
        header = ["parent_id", "email", "name", "phone"]
        _values_update(f"{_parents_tab()}!A1", [header])
        rows = [[*header]]

    header = [str(col).strip() for col in rows[0]]
    changed = False
    for column in required_columns:
        if column not in header:
            header.append(column)
            changed = True

    if changed:
        _values_update(f"{_parents_tab()}!A1:ZZ1", [header])

    return header


def _ensure_pickup_authorizations_header_columns(
    required_columns: list[str],
) -> list[str]:
    tab_name = _pickup_authorizations_tab()
    try:
        rows = _values_get(f"{tab_name}!A:ZZ")
    except SheetsRepositoryError as exc:
        if exc.status_code != 400 or "Unable to parse range" not in str(exc):
            raise
        _create_sheet_if_missing(tab_name)
        rows = []

    if not rows:
        header = ["pickup_id", "child_id", "name", "relationship", "phone"]
        _values_update(f"{tab_name}!A1", [header])
        rows = [[*header]]

    header = [str(col).strip() for col in rows[0]]
    changed = False
    for column in required_columns:
        if column not in header:
            header.append(column)
            changed = True

    if changed:
        _values_update(f"{tab_name}!A1:ZZ1", [header])

    return header


def _ensure_medications_header_columns(required_columns: list[str]) -> list[str]:
    rows = _values_get(f"{_medications_tab()}!A:ZZ")
    if not rows:
        header = ["med_id", "child_id", "date_time", "med_name", "dose", "given_by"]
        _values_update(f"{_medications_tab()}!A1", [header])
        rows = [[*header]]

    header = [str(col).strip() for col in rows[0]]
    changed = False
    for column in required_columns:
        if column not in header:
            header.append(column)
            changed = True

    if changed:
        _values_update(f"{_medications_tab()}!A1:ZZ1", [header])

    return header


def _ensure_photo_meta_header_columns(required_columns: list[str]) -> list[str]:
    rows = _values_get(f"{_photo_meta_tab()}!A:ZZ")
    if not rows:
        header = [
            "file_id",
            "child_id",
            "album",
            "status",
            "uploaded_at",
            "uploaded_by",
            "retention_until",
        ]
        _values_update(f"{_photo_meta_tab()}!A1", [header])
        rows = [[*header]]

    header = [str(col).strip() for col in rows[0]]
    changed = False
    for column in required_columns:
        if column not in header:
            header.append(column)
            changed = True

    if changed:
        _values_update(f"{_photo_meta_tab()}!A1:ZZ1", [header])

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
    if normalized in {"pixelated", "unpixelated", "denied"}:
        return normalized
    return DEFAULT_DOWNLOAD_CONSENT


def _normalize_checkbox_flag(value: Any) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "true", "yes", "ja", "on", "x"}


def _derive_download_consent(payload: dict[str, Any]) -> str:
    if _normalize_checkbox_flag(payload.get("consent__photo_download_denied")):
        return "denied"
    if _normalize_checkbox_flag(payload.get("consent__photo_download_unpixelated")):
        return "unpixelated"
    if _normalize_checkbox_flag(payload.get("consent__photo_download_pixelated")):
        return "pixelated"
    return _normalize_download_consent(str(payload.get("download_consent", "")))


def _sync_child_parent_email(payload: dict[str, Any]) -> None:
    primary_parent_email = str(payload.get("parent1__email", "")).strip()
    if primary_parent_email:
        payload["parent_email"] = primary_parent_email


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
    _ensure_children_header_columns(CHILDREN_REQUIRED_COLUMNS)
    rows = _values_get(f"{_children_tab()}!A:ZZ")
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
        "status": str(child_dict.get("status") or "active").strip() or "active",
        "download_consent": _derive_download_consent(child_dict),
    }
    _sync_child_parent_email(payload)

    header = _ensure_children_header_columns(CHILDREN_REQUIRED_COLUMNS)

    row_values = [str(payload.get(column, "")).strip() for column in header]
    _values_append(f"{_children_tab()}!A:ZZ", [row_values])

    get_children.clear()
    get_child_by_parent_email.clear()
    get_child_by_id.clear()
    return child_id


def update_child(child_id: str, patch_dict: dict[str, Any]) -> None:
    _ensure_children_header_columns(CHILDREN_REQUIRED_COLUMNS)
    row_index, header = _get_row_index_by_id(_children_tab(), "child_id", child_id)

    existing_rows = _values_get(f"{_children_tab()}!A{row_index}:ZZ{row_index}")
    existing_row = existing_rows[0] if existing_rows else []

    current_payload = {
        column: str(existing_row[index]).strip() if index < len(existing_row) else ""
        for index, column in enumerate(header)
    }
    current_payload.update(
        {key: str(value).strip() for key, value in patch_dict.items()}
    )
    _sync_child_parent_email(current_payload)
    current_payload["download_consent"] = _derive_download_consent(current_payload)
    current_payload["status"] = str(current_payload.get("status") or "active").strip()
    if not current_payload["status"]:
        current_payload["status"] = "active"

    row_values = [current_payload.get(column, "") for column in header]
    _values_update(f"{_children_tab()}!A{row_index}:ZZ{row_index}", [row_values])

    get_children.clear()
    get_child_by_parent_email.clear()
    get_child_by_id.clear()


def delete_child(child_id: str) -> None:
    _ensure_children_header_columns(CHILDREN_REQUIRED_COLUMNS)
    row_index, _ = _get_row_index_by_id(_children_tab(), "child_id", child_id)
    _delete_row(_children_tab(), row_index)

    get_children.clear()
    get_child_by_parent_email.clear()
    get_child_by_id.clear()


@st.cache_data(ttl=DEFAULT_CACHE_TTL_SECONDS, show_spinner=False)
def get_parents() -> list[dict[str, str]]:
    _ensure_parents_header_columns(PARENTS_REQUIRED_COLUMNS)
    rows = _values_get(f"{_parents_tab()}!A:ZZ")
    return _to_records(rows)


def add_parent(parent_dict: dict[str, Any]) -> str:
    parent_id = str(parent_dict.get("parent_id") or uuid4().hex)
    payload = {
        **parent_dict,
        "parent_id": parent_id,
        "notifications_opt_in": str(
            parent_dict.get("notifications_opt_in", "false")
        ).strip()
        or "false",
    }

    header = _ensure_parents_header_columns(PARENTS_REQUIRED_COLUMNS)

    row_values = [str(payload.get(column, "")).strip() for column in header]
    _values_append(f"{_parents_tab()}!A:ZZ", [row_values])

    get_parents.clear()
    return parent_id


def update_parent(parent_id: str, patch_dict: dict[str, Any]) -> None:
    _ensure_parents_header_columns(PARENTS_REQUIRED_COLUMNS)
    row_index, header = _get_row_index_by_id(_parents_tab(), "parent_id", parent_id)

    existing_rows = _values_get(f"{_parents_tab()}!A{row_index}:ZZ{row_index}")
    existing_row = existing_rows[0] if existing_rows else []

    current_payload = {
        column: str(existing_row[index]).strip() if index < len(existing_row) else ""
        for index, column in enumerate(header)
    }
    current_payload.update(
        {key: str(value).strip() for key, value in patch_dict.items()}
    )

    row_values = [current_payload.get(column, "") for column in header]
    _values_update(f"{_parents_tab()}!A{row_index}:ZZ{row_index}", [row_values])

    get_parents.clear()


@st.cache_data(ttl=DEFAULT_CACHE_TTL_SECONDS, show_spinner=False)
def get_pickup_authorizations() -> list[dict[str, str]]:
    _ensure_pickup_authorizations_header_columns(PICKUP_AUTHORIZATIONS_REQUIRED_COLUMNS)
    rows = _values_get(f"{_pickup_authorizations_tab()}!A:ZZ")
    return _to_records(rows)


@st.cache_data(ttl=DEFAULT_CACHE_TTL_SECONDS, show_spinner=False)
def get_pickup_authorizations_by_child_id(child_id: str) -> list[dict[str, str]]:
    normalized_child_id = child_id.strip()
    records = [
        authorization
        for authorization in get_pickup_authorizations()
        if authorization.get("child_id", "").strip() == normalized_child_id
    ]
    return sorted(records, key=lambda item: item.get("name", ""))


def add_pickup_authorization(pickup_dict: dict[str, Any]) -> str:
    pickup_id = str(pickup_dict.get("pickup_id") or uuid4().hex)
    payload = {
        **pickup_dict,
        "pickup_id": pickup_id,
        "active": str(pickup_dict.get("active", "true")).strip().lower() or "true",
    }

    header = _ensure_pickup_authorizations_header_columns(
        PICKUP_AUTHORIZATIONS_REQUIRED_COLUMNS
    )
    row_values = [str(payload.get(column, "")).strip() for column in header]
    _values_append(f"{_pickup_authorizations_tab()}!A:ZZ", [row_values])

    get_pickup_authorizations.clear()
    get_pickup_authorizations_by_child_id.clear()
    return pickup_id


def update_pickup_authorization(pickup_id: str, patch_dict: dict[str, Any]) -> None:
    _ensure_pickup_authorizations_header_columns(PICKUP_AUTHORIZATIONS_REQUIRED_COLUMNS)
    row_index, header = _get_row_index_by_id(
        _pickup_authorizations_tab(),
        "pickup_id",
        pickup_id,
    )

    existing_rows = _values_get(
        f"{_pickup_authorizations_tab()}!A{row_index}:ZZ{row_index}"
    )
    existing_row = existing_rows[0] if existing_rows else []

    current_payload = {
        column: str(existing_row[index]).strip() if index < len(existing_row) else ""
        for index, column in enumerate(header)
    }
    current_payload.update(
        {key: str(value).strip() for key, value in patch_dict.items()}
    )
    if "active" in current_payload:
        current_payload["active"] = (
            str(current_payload.get("active", "true")).strip().lower() or "true"
        )

    row_values = [current_payload.get(column, "") for column in header]
    _values_update(
        f"{_pickup_authorizations_tab()}!A{row_index}:ZZ{row_index}",
        [row_values],
    )

    get_pickup_authorizations.clear()
    get_pickup_authorizations_by_child_id.clear()


@st.cache_data(ttl=DEFAULT_CACHE_TTL_SECONDS, show_spinner=False)
def get_medications() -> list[dict[str, str]]:
    _ensure_medications_header_columns(MEDICATIONS_REQUIRED_COLUMNS)
    rows = _values_get(f"{_medications_tab()}!A:ZZ")
    records = _to_records(rows)
    return sorted(records, key=lambda item: item.get("date_time", ""), reverse=True)


@st.cache_data(ttl=DEFAULT_CACHE_TTL_SECONDS, show_spinner=False)
def get_medications_by_child_id(child_id: str) -> list[dict[str, str]]:
    normalized_child_id = child_id.strip()
    records = [
        medication
        for medication in get_medications()
        if medication.get("child_id", "").strip() == normalized_child_id
    ]
    return sorted(records, key=lambda item: item.get("date_time", ""), reverse=True)


def add_medication(medication_dict: dict[str, Any]) -> str:
    med_id = str(medication_dict.get("med_id") or uuid4().hex)
    payload = {
        **medication_dict,
        "med_id": med_id,
    }

    header = _ensure_medications_header_columns(MEDICATIONS_REQUIRED_COLUMNS)
    row_values = [str(payload.get(column, "")).strip() for column in header]
    _values_append(f"{_medications_tab()}!A:ZZ", [row_values])

    get_medications.clear()
    get_medications_by_child_id.clear()
    return med_id


@st.cache_data(ttl=DEFAULT_CACHE_TTL_SECONDS, show_spinner=False)
def get_photo_meta_records() -> list[dict[str, str]]:
    _ensure_photo_meta_header_columns(PHOTO_META_REQUIRED_COLUMNS)
    rows = _values_get(f"{_photo_meta_tab()}!A:ZZ")
    return _to_records(rows)


@st.cache_data(ttl=DEFAULT_CACHE_TTL_SECONDS, show_spinner=False)
def get_photo_meta_by_file_id(file_id: str) -> dict[str, str] | None:
    normalized_file_id = file_id.strip()
    for record in get_photo_meta_records():
        if record.get("file_id", "").strip() == normalized_file_id:
            return record
    return None


def add_photo_meta(meta_dict: dict[str, Any]) -> str:
    file_id = str(meta_dict.get("file_id", "")).strip()
    if not file_id:
        raise ValueError("file_id ist erforderlich.")

    if get_photo_meta_by_file_id(file_id):
        raise ValueError(f"photo_meta mit file_id='{file_id}' existiert bereits.")

    payload = {**meta_dict, "file_id": file_id}
    header = _ensure_photo_meta_header_columns(PHOTO_META_REQUIRED_COLUMNS)
    row_values = [str(payload.get(column, "")).strip() for column in header]
    _values_append(f"{_photo_meta_tab()}!A:ZZ", [row_values])

    get_photo_meta_records.clear()
    get_photo_meta_by_file_id.clear()
    return file_id


def upsert_photo_meta(file_id: str, patch_dict: dict[str, Any]) -> None:
    normalized_file_id = file_id.strip()
    if not normalized_file_id:
        raise ValueError("file_id ist erforderlich.")

    _ensure_photo_meta_header_columns(PHOTO_META_REQUIRED_COLUMNS)

    try:
        row_index, header = _get_row_index_by_id(
            _photo_meta_tab(),
            "file_id",
            normalized_file_id,
        )
    except KeyError:
        payload = {"file_id": normalized_file_id}
        payload.update({key: str(value).strip() for key, value in patch_dict.items()})
        row_values = [
            str(payload.get(column, "")).strip()
            for column in PHOTO_META_REQUIRED_COLUMNS
        ]
        _values_append(f"{_photo_meta_tab()}!A:ZZ", [row_values])
    else:
        existing_rows = _values_get(f"{_photo_meta_tab()}!A{row_index}:ZZ{row_index}")
        existing_row = existing_rows[0] if existing_rows else []
        current_payload = {
            column: str(existing_row[index]).strip()
            if index < len(existing_row)
            else ""
            for index, column in enumerate(header)
        }
        current_payload.update(
            {key: str(value).strip() for key, value in patch_dict.items()}
        )
        row_values = [current_payload.get(column, "") for column in header]
        _values_update(f"{_photo_meta_tab()}!A{row_index}:ZZ{row_index}", [row_values])

    get_photo_meta_records.clear()
    get_photo_meta_by_file_id.clear()
