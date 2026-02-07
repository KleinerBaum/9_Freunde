from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import streamlit as st

from config import get_app_config

try:
    import firebase_admin
    from firebase_admin import credentials
except ImportError:  # pragma: no cover - depends on optional runtime package
    firebase_admin = None
    credentials = None

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:  # pragma: no cover - depends on optional runtime package
    service_account = None
    build = None


firebase_app: Any | None = None


def init_firebase() -> None:
    """Initialisiert firebase_admin nur im Google-Modus."""
    global firebase_app

    app_config = get_app_config()
    if app_config.storage_mode != "google":
        return

    if firebase_admin is None or credentials is None:
        return

    if firebase_app:
        return

    try:
        cred_info = app_config.google.service_account if app_config.google else None
        if cred_info:
            cred = credentials.Certificate(cred_info)
            firebase_app = firebase_admin.initialize_app(cred)
        elif not firebase_admin._apps:
            firebase_app = firebase_admin.initialize_app()
        else:
            firebase_app = firebase_admin.get_app()
    except Exception as exc:  # pragma: no cover - external service setup
        print("Firebase Initialisierung fehlgeschlagen:", exc)


def _safe_name(name: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in name)


class DriveAgent:
    def __init__(self) -> None:
        app_config = get_app_config()
        self.storage_mode = app_config.storage_mode
        self.local_drive_root = app_config.local.drive_root
        self.index_file = self.local_drive_root / "drive_index.json"

        if self.storage_mode == "google":
            if service_account is None or build is None:
                raise RuntimeError(
                    "Google API-Pakete fehlen. Bitte requirements installieren."
                )
            if app_config.google is None:
                raise RuntimeError("Google-Konfiguration fehlt.")
            scopes = ["https://www.googleapis.com/auth/drive"]
            drive_credentials = service_account.Credentials.from_service_account_info(
                app_config.google.service_account,
                scopes=scopes,
            )
            self.service = build("drive", "v3", credentials=drive_credentials)
        else:
            self.service = None
            self.local_drive_root.mkdir(parents=True, exist_ok=True)

    def _read_index(self) -> dict[str, dict[str, str]]:
        if not self.index_file.exists():
            return {}
        return json.loads(self.index_file.read_text(encoding="utf-8"))

    def _write_index(self, index: dict[str, dict[str, str]]) -> None:
        self.index_file.write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_files(
        self, folder_id: str, mime_type_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Gibt eine Liste der Dateien in einem Ordner zurück."""
        if self.storage_mode == "google":
            query = f"'{folder_id}' in parents and trashed=false"
            if mime_type_filter:
                query += f" and mimeType contains '{mime_type_filter}'"
            results = (
                self.service.files()
                .list(q=query, fields="files(id, name, mimeType)")
                .execute()
            )
            return results.get("files", [])

        index = self._read_index()
        files: list[dict[str, Any]] = []
        for file_id, metadata in index.items():
            if metadata.get("folder_id") != folder_id:
                continue
            mime_type = metadata.get("mimeType", "")
            if mime_type_filter and mime_type_filter not in mime_type:
                continue
            files.append(
                {"id": file_id, "name": metadata.get("name"), "mimeType": mime_type}
            )
        files.sort(key=lambda item: str(item.get("name", "")))
        return files

    @st.cache_data(show_spinner=False)
    def download_file(self, file_id: str) -> bytes:
        """Lädt eine Datei herunter."""
        if self.storage_mode == "google":
            request = self.service.files().get_media(fileId=file_id)
            return request.execute()

        index = self._read_index()
        metadata = index.get(file_id)
        if not metadata:
            raise FileNotFoundError(f"Datei mit ID '{file_id}' nicht gefunden.")
        path = Path(metadata["path"])
        return path.read_bytes()

    def upload_file(
        self,
        name: str,
        content_bytes: bytes,
        mime_type: str,
        parent_folder_id: str | None,
    ) -> str | None:
        """Lädt eine Datei hoch und gibt die File-ID zurück."""
        if self.storage_mode == "google":
            from io import BytesIO

            from googleapiclient.http import MediaIoBaseUpload

            media = MediaIoBaseUpload(
                BytesIO(content_bytes), mimetype=mime_type, resumable=False
            )
            metadata: dict[str, Any] = {"name": name}
            if parent_folder_id:
                metadata["parents"] = [parent_folder_id]
            file = (
                self.service.files()
                .create(body=metadata, media_body=media, fields="id")
                .execute()
            )
            return file.get("id")

        folder_id = parent_folder_id or "root"
        folder_path = self.local_drive_root / folder_id
        folder_path.mkdir(parents=True, exist_ok=True)

        file_id = uuid.uuid4().hex
        safe_file_name = _safe_name(name)
        path = folder_path / f"{file_id}_{safe_file_name}"
        path.write_bytes(content_bytes)

        index = self._read_index()
        index[file_id] = {
            "name": name,
            "mimeType": mime_type,
            "folder_id": folder_id,
            "path": str(path),
        }
        self._write_index(index)
        self.download_file.clear()
        return file_id

    def create_folder(
        self, name: str, parent_folder_id: str | None = None
    ) -> str | None:
        """Erstellt einen neuen Ordner und gibt die ID zurück."""
        if self.storage_mode == "google":
            folder_metadata: dict[str, Any] = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_folder_id:
                folder_metadata["parents"] = [parent_folder_id]
            folder = (
                self.service.files().create(body=folder_metadata, fields="id").execute()
            )
            return folder.get("id")

        folder_id = uuid.uuid4().hex
        folder_path = self.local_drive_root / folder_id
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_id
