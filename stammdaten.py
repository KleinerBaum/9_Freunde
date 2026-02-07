from __future__ import annotations

import json
import uuid
from typing import Any

import streamlit as st

from config import get_app_config
from storage import DriveAgent, init_firebase

try:
    from firebase_admin import firestore
except ImportError:  # pragma: no cover - depends on optional runtime package
    firestore = None


class StammdatenManager:
    def __init__(self) -> None:
        self.config = get_app_config()
        self.storage_mode = self.config.storage_mode
        self.children_file = self.config.local.children_file

        init_firebase()
        self.db: Any | None = None

        if self.storage_mode == "google":
            if firestore is None:
                st.warning(
                    "Das Paket 'firebase-admin' ist nicht installiert. "
                    "Stammdaten sind aktuell nur eingeschränkt verfügbar.",
                )
                return

            try:
                self.db = firestore.client()
            except Exception as exc:
                st.error(f"Datenbank-Verbindung fehlgeschlagen: {exc}")
        else:
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
            children: list[dict[str, Any]] = []
            if not self.db:
                return children

            docs = self.db.collection("children").stream()
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                children.append(data)
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
            if not self.db:
                raise RuntimeError("Keine Datenbankverbindung.")

            child_data: dict[str, Any] = {"name": name, "parent_email": parent_email}
            if folder_id:
                child_data["folder_id"] = folder_id

            doc_ref = self.db.collection("children").document()
            doc_ref.set(child_data)
            return doc_ref.id

        child_id = uuid.uuid4().hex
        child_data = {
            "id": child_id,
            "name": name,
            "parent_email": parent_email,
        }
        if folder_id:
            child_data["folder_id"] = folder_id

        children = self._read_local_children()
        children.append(child_data)
        self._write_local_children(children)
        return child_id

    def get_child_by_parent(self, parent_email: str) -> dict[str, Any] | None:
        """Liefert den Kind-Datensatz für eine Eltern-E-Mail."""
        if self.storage_mode == "google":
            if not self.db:
                return None

            query = (
                self.db.collection("children")
                .where("parent_email", "==", parent_email)
                .stream()
            )
            for doc in query:
                data = doc.to_dict()
                data["id"] = doc.id
                return data
            return None

        for child in self._read_local_children():
            if child.get("parent_email") == parent_email:
                return child
        return None

    def update_child(self, child_id: str, new_data: dict[str, Any]) -> None:
        """Aktualisiert Felder des Kindes mit der ID child_id."""
        if self.storage_mode == "google":
            if not self.db:
                raise RuntimeError("Keine Datenbankverbindung.")
            self.db.collection("children").document(child_id).update(new_data)
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
            if not self.db:
                raise RuntimeError("Keine Datenbankverbindung.")
            self.db.collection("children").document(child_id).delete()
            return

        children = self._read_local_children()
        filtered = [child for child in children if child.get("id") != child_id]
        self._write_local_children(filtered)
