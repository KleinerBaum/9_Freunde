from __future__ import annotations

from typing import Any

import streamlit as st

from storage import DriveAgent, init_firebase

try:
    from firebase_admin import firestore
except ImportError:  # pragma: no cover - depends on optional runtime package
    firestore = None


class StammdatenManager:
    def __init__(self) -> None:
        # Firebase Initialisierung (Firestore)
        init_firebase()
        self.db: Any | None = None

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

    def get_children(self) -> list[dict[str, Any]]:
        """Lädt alle Kinder-Datensätze aus der Datenbank."""
        children: list[dict[str, Any]] = []
        if not self.db:
            return children

        docs = self.db.collection("children").stream()
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            children.append(data)

        children.sort(key=lambda item: item.get("name", ""))
        return children

    def add_child(self, name: str, parent_email: str) -> str:
        """Fügt ein Kind hinzu und erstellt optional einen Drive-Ordner."""
        if not self.db:
            raise RuntimeError("Keine Datenbankverbindung.")

        child_data = {"name": name, "parent_email": parent_email}
        doc_ref = self.db.collection("children").document()
        doc_ref.set(child_data)
        child_id = doc_ref.id

        folder_id: str | None = None
        try:
            drive_agent = DriveAgent()
            main_folder = st.secrets.get("gcp", {}).get("photos_folder_id")
            folder_id = drive_agent.create_folder(name, parent_folder_id=main_folder)
        except Exception as exc:
            print("Fehler beim Anlegen des Drive-Ordners:", exc)

        if folder_id:
            try:
                doc_ref.update({"folder_id": folder_id})
            except Exception as exc:
                print("Fehler beim Speichern der Ordner-ID:", exc)

        return child_id

    def get_child_by_parent(self, parent_email: str) -> dict[str, Any] | None:
        """Liefert den Kind-Datensatz für eine Eltern-E-Mail."""
        if not self.db:
            return None

        query = self.db.collection("children").where("parent_email", "==", parent_email).stream()
        for doc in query:
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        return None

    def update_child(self, child_id: str, new_data: dict[str, Any]) -> None:
        """Aktualisiert Felder des Kindes mit der ID child_id."""
        if not self.db:
            raise RuntimeError("Keine Datenbankverbindung.")
        self.db.collection("children").document(child_id).update(new_data)

    def delete_child(self, child_id: str) -> None:
        """Löscht den Kind-Datensatz."""
        if not self.db:
            raise RuntimeError("Keine Datenbankverbindung.")
        self.db.collection("children").document(child_id).delete()
