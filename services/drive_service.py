from __future__ import annotations

from io import BytesIO
from typing import Any

import streamlit as st
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from config import get_app_config
from services import sheets_repo
from services.google_clients import get_drive_client


class DriveServiceError(RuntimeError):
    """Domänenspezifischer Fehler für Drive-Zugriffe."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _translate_http_error(exc: HttpError) -> DriveServiceError:
    status = getattr(exc.resp, "status", None)
    if status in (403, 404):
        return DriveServiceError(
            "Kein Zugriff auf den Drive-Ordner oder Datei nicht gefunden. "
            "Bitte den Zielordner mit dem Service-Account teilen.",
            status_code=status,
        )
    return DriveServiceError(f"Drive API Fehler: {exc}", status_code=status)


def create_folder(name: str, parent_id: str) -> str:
    drive = get_drive_client()
    metadata: dict[str, Any] = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }

    try:
        created = (
            drive.files()
            .create(body=metadata, fields="id", supportsAllDrives=True)
            .execute()
        )
    except HttpError as exc:
        raise _translate_http_error(exc) from exc

    return created["id"]


def ensure_child_photo_folder(child_id: str) -> str:
    normalized_child_id = child_id.strip()
    child = sheets_repo.get_child_by_id(normalized_child_id)
    if not child:
        raise DriveServiceError(f"Kind mit ID '{child_id}' nicht gefunden.")

    existing_folder_id = str(child.get("photo_folder_id", "")).strip()
    if existing_folder_id:
        return existing_folder_id

    app_config = get_app_config()
    if app_config.google is None:
        raise DriveServiceError(
            "Google-Konfiguration fehlt, Foto-Ordner kann nicht erstellt werden."
        )

    folder_id = create_folder(
        name=normalized_child_id,
        parent_id=app_config.google.drive_photos_root_folder_id,
    )
    sheets_repo.update_child(normalized_child_id, {"photo_folder_id": folder_id})
    return folder_id


def upload_bytes_to_folder(
    folder_id: str,
    filename: str,
    file_bytes: bytes,
    mime_type: str,
) -> str:
    drive = get_drive_client()
    media = MediaIoBaseUpload(BytesIO(file_bytes), mimetype=mime_type, resumable=False)

    metadata: dict[str, Any] = {
        "name": filename,
        "parents": [folder_id],
    }

    try:
        created = (
            drive.files()
            .create(
                body=metadata,
                media_body=media,
                fields="id, name",
                supportsAllDrives=True,
            )
            .execute()
        )
    except HttpError as exc:
        raise _translate_http_error(exc) from exc

    return created["id"]


def list_files_in_folder(folder_id: str) -> list[dict[str, Any]]:
    drive = get_drive_client()
    q = f"'{folder_id}' in parents and trashed = false"

    try:
        res = (
            drive.files()
            .list(
                q=q,
                fields="files(id, name, mimeType, modifiedTime)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageSize=1000,
                orderBy="modifiedTime desc",
            )
            .execute()
        )
    except HttpError as exc:
        raise _translate_http_error(exc) from exc

    return res.get("files", [])


@st.cache_data(show_spinner=False)
def download_file(file_id: str) -> bytes:
    drive = get_drive_client()
    try:
        request = drive.files().get_media(fileId=file_id, supportsAllDrives=True)
        return request.execute()
    except HttpError as exc:
        raise _translate_http_error(exc) from exc
