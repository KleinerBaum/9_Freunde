from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import streamlit as st
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from config import get_app_config
from onedrive_auth import OneDriveAuthError, get_graph_client, get_onedrive_folder
from services.google_clients import get_drive_client

DEFAULT_ONEDRIVE_FOLDER_PATH = "Documents/9 Freunde"


class DriveServiceError(RuntimeError):
    """Domänenspezifischer Fehler für Drive-Zugriffe."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        cause: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.cause = cause


def _is_onedrive_enabled() -> bool:
    onedrive_config = st.secrets.get("onedrive", {})
    return bool(
        isinstance(onedrive_config, dict) and onedrive_config.get("enabled", False)
    )


def _onedrive_folder_path() -> str:
    onedrive_config = st.secrets.get("onedrive", {})
    if isinstance(onedrive_config, dict):
        configured_path = str(onedrive_config.get("folder_path", "")).strip()
        if configured_path:
            return configured_path
    return DEFAULT_ONEDRIVE_FOLDER_PATH


def translate_http_error(exc: Exception) -> DriveServiceError:
    if isinstance(exc, OneDriveAuthError):
        if exc.reason == "permission":
            return DriveServiceError(
                "Kein Zugriff auf den OneDrive-Ordner. Bitte App-Rechte und "
                "Berechtigungen für den Zielordner prüfen.",
                status_code=exc.status_code,
                cause="forbidden",
            )
        if exc.reason == "path":
            return DriveServiceError(
                "OneDrive-Ordner oder Datei nicht gefunden. Bitte Pfad und "
                "Ziel-ID prüfen.",
                status_code=exc.status_code,
                cause="not_found",
            )
        if exc.reason in {"auth", "config"}:
            return DriveServiceError(
                "OneDrive-Authentifizierung oder Konfiguration ist ungültig. "
                "Bitte [onedrive]-Secrets prüfen.",
                status_code=exc.status_code,
                cause=exc.reason,
            )
        return DriveServiceError(
            f"OneDrive API Fehler: {exc}",
            status_code=exc.status_code,
            cause="api_error",
        )

    if not isinstance(exc, HttpError):
        return DriveServiceError(f"Drive API Fehler: {exc}", cause="api_error")

    status = int(getattr(exc.resp, "status", 0) or 0)
    if status == 403:
        return DriveServiceError(
            "Kein Zugriff auf den Drive-Ordner. Bitte den Zielordner mit dem "
            "Service-Account teilen.",
            status_code=status,
            cause="forbidden",
        )
    if status == 404:
        return DriveServiceError(
            "Drive-Ordner oder Datei nicht gefunden. Bitte die konfigurierte ID "
            "prüfen.",
            status_code=status,
            cause="not_found",
        )
    return DriveServiceError(
        f"Drive API Fehler: {exc}",
        status_code=status if status else None,
        cause="api_error",
    )


def create_folder(name: str, parent_id: str | None = None) -> str:
    if _is_onedrive_enabled():
        client = get_graph_client()
        parent_path = (
            f"{client.drive_base_path}/items/{parent_id}/children"
            if parent_id
            else f"{client.drive_base_path}/root/children"
        )
        payload = {
            "name": name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename",
        }
        try:
            created = client.request(
                "POST",
                parent_path,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload).encode("utf-8"),
            ).json()
        except OneDriveAuthError as exc:
            raise translate_http_error(exc) from exc
        return str(created.get("id", "")).strip()

    drive = get_drive_client()
    metadata: dict[str, Any] = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    try:
        created = (
            drive.files()
            .create(body=metadata, fields="id", supportsAllDrives=True)
            .execute()
        )
    except HttpError as exc:
        raise translate_http_error(exc) from exc

    return created["id"]


def get_photos_root_folder_id() -> str:
    if _is_onedrive_enabled():
        folder = get_onedrive_folder(_onedrive_folder_path())
        if not folder.id:
            raise DriveServiceError(
                "OneDrive-Ordner-ID konnte nicht aufgelöst werden.",
                cause="not_found",
            )
        return folder.id

    app_config = get_app_config()
    if app_config.google is None:
        raise DriveServiceError(
            "Google-Konfiguration fehlt, zentraler Foto-Ordner ist nicht verfügbar."
        )
    return app_config.google.drive_photos_root_folder_id


def upload_bytes_to_folder(
    folder_id: str | None,
    filename: str,
    file_bytes: bytes,
    mime_type: str,
) -> str:
    if _is_onedrive_enabled():
        client = get_graph_client()
        normalized_name = filename.strip()
        if not normalized_name:
            raise DriveServiceError("Dateiname darf nicht leer sein.", cause="invalid")

        target_path = (
            f"{client.drive_base_path}/items/{folder_id}:/{normalized_name}:/content"
            if folder_id
            else (
                f"{client.drive_base_path}/root:/"
                f"{_onedrive_folder_path().strip('/')}/{normalized_name}:/content"
            )
        )
        try:
            created = client.request(
                "PUT",
                target_path,
                headers={"Content-Type": mime_type or "application/octet-stream"},
                data=file_bytes,
            ).json()
        except OneDriveAuthError as exc:
            raise translate_http_error(exc) from exc
        return str(created.get("id", "")).strip()

    drive = get_drive_client()
    media = MediaIoBaseUpload(BytesIO(file_bytes), mimetype=mime_type, resumable=False)

    metadata: dict[str, Any] = {"name": filename}
    if folder_id:
        metadata["parents"] = [folder_id]

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
        raise translate_http_error(exc) from exc

    return created["id"]


def list_files_in_folder(
    folder_id: str,
    mime_type_filter: str | None = None,
) -> list[dict[str, Any]]:
    if _is_onedrive_enabled():
        client = get_graph_client()
        try:
            response = client.request(
                "GET",
                f"{client.drive_base_path}/items/{folder_id}/children",
                params={"$top": 1000},
            )
        except OneDriveAuthError as exc:
            raise translate_http_error(exc) from exc

        payload = response.json().get("value", [])
        if not isinstance(payload, list):
            return []

        files = [
            {
                "id": str(item.get("id", "")).strip(),
                "name": str(item.get("name", "")).strip(),
                "mimeType": str(item.get("file", {}).get("mimeType", "")).strip(),
                "modifiedTime": str(item.get("lastModifiedDateTime", "")).strip(),
            }
            for item in payload
            if isinstance(item, dict)
        ]

        normalized_filter = (mime_type_filter or "").strip().lower()
        if not normalized_filter:
            return files

        return [
            item
            for item in files
            if normalized_filter in str(item.get("mimeType", "")).lower()
        ]

    drive = get_drive_client()
    q = f"'{folder_id}' in parents and trashed = false"

    normalized_filter = (mime_type_filter or "").strip().lower()
    query_filter = normalized_filter.rstrip("/")
    if query_filter:
        q += f" and mimeType contains '{query_filter}'"

    files: list[dict[str, Any]] = []
    page_token: str | None = None

    try:
        while True:
            res = (
                drive.files()
                .list(
                    q=q,
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    corpora="allDrives",
                    pageSize=1000,
                    orderBy="modifiedTime desc",
                    pageToken=page_token,
                )
                .execute()
            )
            files.extend(res.get("files", []))
            page_token = res.get("nextPageToken")
            if not page_token:
                break
    except HttpError as exc:
        raise translate_http_error(exc) from exc

    if not normalized_filter:
        return files

    if normalized_filter.endswith("/"):
        return [
            item
            for item in files
            if str(item.get("mimeType", "")).lower().startswith(normalized_filter)
        ]

    return [
        item
        for item in files
        if normalized_filter in str(item.get("mimeType", "")).lower()
    ]


@st.cache_data(show_spinner=False)
def download_file(file_id: str) -> bytes:
    if _is_onedrive_enabled():
        client = get_graph_client()
        try:
            response = client.request(
                "GET", f"{client.drive_base_path}/items/{file_id}/content"
            )
        except OneDriveAuthError as exc:
            raise translate_http_error(exc) from exc
        return response.content

    drive = get_drive_client()
    try:
        request = drive.files().get_media(fileId=file_id, supportsAllDrives=True)
        return request.execute()
    except HttpError as exc:
        raise translate_http_error(exc) from exc
