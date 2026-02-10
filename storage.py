from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import streamlit as st
from googleapiclient.errors import HttpError

from config import get_app_config
from services.drive_service import (
    create_folder as create_google_folder,
    download_file as download_google_file,
    list_files_in_folder,
    translate_http_error,
    upload_bytes_to_folder,
)


def _safe_name(name: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in name)


class DriveAgent:
    def __init__(self) -> None:
        app_config = get_app_config()
        self.storage_mode = app_config.storage_mode
        self.local_drive_root = app_config.local.drive_root
        self.index_file = self.local_drive_root / "drive_index.json"

        if self.storage_mode != "google":
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
            try:
                return list_files_in_folder(folder_id, mime_type_filter)
            except HttpError as exc:
                raise translate_http_error(exc) from exc

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
            return download_google_file(file_id)

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
            try:
                return upload_bytes_to_folder(
                    parent_folder_id,
                    name,
                    content_bytes,
                    mime_type,
                )
            except HttpError as exc:
                raise translate_http_error(exc) from exc

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
            return create_google_folder(name=name, parent_id=parent_folder_id)

        folder_id = uuid.uuid4().hex
        folder_path = self.local_drive_root / folder_id
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_id
