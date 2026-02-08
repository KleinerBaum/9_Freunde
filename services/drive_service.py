from __future__ import annotations

from io import BytesIO
from typing import Any

import streamlit as st
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

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
