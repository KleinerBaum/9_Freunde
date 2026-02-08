from __future__ import annotations

import json
import uuid
from typing import Any

import streamlit as st

from config import get_app_config
from services import sheets_repo
from storage import DriveAgent


def _normalize_child_record(child: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(child)
    if "id" not in normalized and "child_id" in normalized:
        normalized["id"] = normalized["child_id"]
    return normalized


class StammdatenManager:
    def __init__(self) -> None:
        self.config = get_app_config()
        self.storage_mode = self.config.storage_mode
        self.children_file = self.config.local.children_file

        if self.storage_mode != "google":
            self.children_file.parent.mkdir(parents=True, exist_ok=True)
            if not self.children_file.exists():
                self.children_file.write_text("[]", encoding="utf-8")

    def _read_local_children(self) -> list[dict[str, Any]]:
        if not self.children_file.exists():
            return []
        data = json.loads(self.children_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _write_local_children(self, children: list[dict[str, Any]]) -> None:
        self.children_file.write_text(
            json.dumps(children, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_children(self) -> list[dict[str, Any]]:
        """Lädt alle Kinder-Datensätze."""
        if self.storage_mode == "google":
            children = [
                _normalize_child_record(child) for child in sheets_repo.get_children()
            ]
        else:
            children = self._read_local_children()

        children.sort(key=lambda item: item.get("name", ""))
        return children

    def add_child(self, name: str, parent_email: str) -> str:
        """Fügt ein Kind hinzu und erstellt optional einen Drive-Ordner."""
        folder_id: str | None = None
        try:
            drive_agent = DriveAgent()
            parent_folder_id = (
                self.config.google.photos_folder_id
                if self.storage_mode == "google" and self.config.google
                else None
            )
            folder_id = drive_agent.create_folder(
                name, parent_folder_id=parent_folder_id
            )
        except Exception as exc:
            print("Fehler beim Anlegen des Ordners:", exc)

        if self.storage_mode == "google":
            child_data: dict[str, Any] = {"name": name, "parent_email": parent_email}
            if folder_id:
                child_data["folder_id"] = folder_id
                child_data["photo_folder_id"] = folder_id
            return sheets_repo.add_child(child_data)

        child_id = uuid.uuid4().hex
        child_data = {
            "id": child_id,
            "name": name,
            "parent_email": parent_email,
        }
        if folder_id:
            child_data["folder_id"] = folder_id
            child_data["photo_folder_id"] = folder_id

        children = self._read_local_children()
        children.append(child_data)
        self._write_local_children(children)
        return child_id

    def get_child_by_parent(self, parent_email: str) -> dict[str, Any] | None:
        """Liefert den Kind-Datensatz für eine Eltern-E-Mail."""
        if self.storage_mode == "google":
            child = sheets_repo.get_child_by_parent_email(parent_email)
            return _normalize_child_record(child) if child else None

        for child in self._read_local_children():
            if child.get("parent_email") == parent_email:
                return child
        return None

    def get_child_by_id(self, child_id: str) -> dict[str, Any] | None:
        """Liefert den Kind-Datensatz über die Kind-ID."""
        if self.storage_mode == "google":
            child = sheets_repo.get_child_by_id(child_id)
            return _normalize_child_record(child) if child else None

        for child in self._read_local_children():
            if child.get("id") == child_id:
                return child
        return None

    def update_child(self, child_id: str, new_data: dict[str, Any]) -> None:
        """Aktualisiert Felder des Kindes mit der ID child_id."""
        if self.storage_mode == "google":
            sheets_repo.update_child(child_id, new_data)
            return

        children = self._read_local_children()
        for index, child in enumerate(children):
            if child.get("id") == child_id:
                children[index] = {**child, **new_data}
                self._write_local_children(children)
                return
        raise KeyError(f"Kind mit ID '{child_id}' wurde nicht gefunden.")

    def delete_child(self, child_id: str) -> None:
        """Löscht den Kind-Datensatz."""
        if self.storage_mode == "google":
            st.warning("Löschen über Google Sheets ist derzeit nicht implementiert.")
            return

        children = self._read_local_children()
        filtered = [child for child in children if child.get("id") != child_id]
        self._write_local_children(filtered)
