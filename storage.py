from __future__ import annotations

from typing import Any

import streamlit as st

try:
    import firebase_admin
    from firebase_admin import credentials
except ImportError:  # pragma: no cover - depends on optional runtime package
    firebase_admin = None
    credentials = None


# Firebase initialisieren (einmalig)
firebase_app: Any | None = None


def init_firebase() -> None:
    """Initialisiert firebase_admin, falls das Paket verfügbar ist."""
    global firebase_app

    if firebase_admin is None or credentials is None:
        return

    if firebase_app:
        return

    try:
        # Versuche, Dienstkonto-Daten aus Secrets zu laden
        cred_info = st.secrets.get("gcp_service_account")
        if cred_info:
            cred = credentials.Certificate(cred_info)
            firebase_app = firebase_admin.initialize_app(cred)
        elif not firebase_admin._apps:
            firebase_app = firebase_admin.initialize_app()
        else:
            firebase_app = firebase_admin.get_app()
    except Exception as exc:  # pragma: no cover - external service setup
        print("Firebase Initialisierung fehlgeschlagen:", exc)


# Google Drive API Anbindung
from google.oauth2 import service_account
from googleapiclient.discovery import build


class DriveAgent:
    def __init__(self) -> None:
        # Authentifizierung für Google Drive API
        service_account_info = st.secrets.get("gcp_service_account") or st.secrets.get("gcp")
        if not service_account_info:
            raise RuntimeError("Drive Service-Account nicht konfiguriert.")
        scopes = ["https://www.googleapis.com/auth/drive"]
        drive_credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=scopes,
        )
        self.service = build("drive", "v3", credentials=drive_credentials)

    def list_files(self, folder_id: str, mime_type_filter: str | None = None) -> list[dict[str, Any]]:
        """Gibt eine Liste der Dateien in einem Ordner zurück."""
        query = f"'{folder_id}' in parents and trashed=false"
        if mime_type_filter:
            query += f" and mimeType contains '{mime_type_filter}'"
        results = self.service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        return results.get("files", [])

    @st.cache_data(show_spinner=False)
    def download_file(self, file_id: str) -> bytes:
        """Lädt eine Datei von Drive herunter."""
        request = self.service.files().get_media(fileId=file_id)
        data = request.execute()
        return data

    def upload_file(self, name: str, content_bytes: bytes, mime_type: str, parent_folder_id: str | None) -> str | None:
        """Lädt eine Datei nach Google Drive hoch und gibt die File-ID zurück."""
        from io import BytesIO

        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(BytesIO(content_bytes), mimetype=mime_type, resumable=False)
        metadata: dict[str, Any] = {"name": name}
        if parent_folder_id:
            metadata["parents"] = [parent_folder_id]
        file = self.service.files().create(body=metadata, media_body=media, fields="id").execute()
        return file.get("id")

    def create_folder(self, name: str, parent_folder_id: str | None = None) -> str | None:
        """Erstellt einen neuen Ordner in Drive und gibt die ID zurück."""
        folder_metadata: dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_folder_id:
            folder_metadata["parents"] = [parent_folder_id]
        folder = self.service.files().create(body=folder_metadata, fields="id").execute()
        return folder.get("id")
