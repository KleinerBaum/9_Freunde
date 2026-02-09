from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any


from config import get_app_config
from services import sheets_repo
from storage import DriveAgent

DEFAULT_DOWNLOAD_CONSENT = "pixelated"


def _normalize_download_consent(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"pixelated", "unpixelated"}:
        return normalized
    return DEFAULT_DOWNLOAD_CONSENT


def _normalize_child_record(child: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(child)
    if "id" not in normalized and "child_id" in normalized:
        normalized["id"] = normalized["child_id"]
    normalized["download_consent"] = _normalize_download_consent(
        normalized.get("download_consent")
    )
    return normalized


class StammdatenManager:
    def __init__(self) -> None:
        self.config = get_app_config()
        self.storage_mode = self.config.storage_mode
        self.children_file = self.config.local.children_file
        self.parents_file = self.config.local.parents_file
        self.consents_file = self.config.local.consents_file
        self.pickup_authorizations_file = self.config.local.pickup_authorizations_file
        self.medications_file = self.config.local.medications_file
        self.photo_meta_file = self.config.local.photo_meta_file

        if self.storage_mode != "google":
            self.children_file.parent.mkdir(parents=True, exist_ok=True)
            if not self.children_file.exists():
                self.children_file.write_text("[]", encoding="utf-8")
            if not self.parents_file.exists():
                self.parents_file.write_text("[]", encoding="utf-8")
            if not self.consents_file.exists():
                self.consents_file.write_text("[]", encoding="utf-8")
            if not self.pickup_authorizations_file.exists():
                self.pickup_authorizations_file.write_text("[]", encoding="utf-8")
            if not self.medications_file.exists():
                self.medications_file.write_text("[]", encoding="utf-8")
            if not self.photo_meta_file.exists():
                self.photo_meta_file.write_text("[]", encoding="utf-8")

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

    def _read_local_parents(self) -> list[dict[str, Any]]:
        if not self.parents_file.exists():
            return []
        data = json.loads(self.parents_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _write_local_parents(self, parents: list[dict[str, Any]]) -> None:
        self.parents_file.write_text(
            json.dumps(parents, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_local_consents(self) -> list[dict[str, Any]]:
        if not self.consents_file.exists():
            return []
        data = json.loads(self.consents_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _write_local_consents(self, consents: list[dict[str, Any]]) -> None:
        self.consents_file.write_text(
            json.dumps(consents, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_local_pickup_authorizations(self) -> list[dict[str, Any]]:
        if not self.pickup_authorizations_file.exists():
            return []
        data = json.loads(self.pickup_authorizations_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _write_local_pickup_authorizations(
        self,
        pickup_authorizations: list[dict[str, Any]],
    ) -> None:
        self.pickup_authorizations_file.write_text(
            json.dumps(pickup_authorizations, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_local_medications(self) -> list[dict[str, Any]]:
        if not self.medications_file.exists():
            return []
        data = json.loads(self.medications_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _write_local_medications(self, medications: list[dict[str, Any]]) -> None:
        self.medications_file.write_text(
            json.dumps(medications, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_local_photo_meta(self) -> list[dict[str, Any]]:
        if not self.photo_meta_file.exists():
            return []
        data = json.loads(self.photo_meta_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _write_local_photo_meta(self, records: list[dict[str, Any]]) -> None:
        self.photo_meta_file.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_children(self) -> list[dict[str, Any]]:
        """Lädt alle Kinder-Datensätze."""
        if self.storage_mode == "google":
            children = [
                _normalize_child_record(child) for child in sheets_repo.get_children()
            ]
        else:
            children = [
                _normalize_child_record(child) for child in self._read_local_children()
            ]

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
            child_data: dict[str, Any] = {
                "name": name,
                "parent_email": parent_email,
                "status": "active",
            }
            if folder_id:
                child_data["folder_id"] = folder_id
                child_data["photo_folder_id"] = folder_id
            return sheets_repo.add_child(child_data)

        child_id = uuid.uuid4().hex
        child_data = {
            "id": child_id,
            "name": name,
            "parent_email": parent_email,
            "download_consent": DEFAULT_DOWNLOAD_CONSENT,
            "status": "active",
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
                return _normalize_child_record(child)
        return None

    def get_child_by_id(self, child_id: str) -> dict[str, Any] | None:
        """Liefert den Kind-Datensatz über die Kind-ID."""
        if self.storage_mode == "google":
            child = sheets_repo.get_child_by_id(child_id)
            return _normalize_child_record(child) if child else None

        for child in self._read_local_children():
            if child.get("id") == child_id:
                return _normalize_child_record(child)
        return None

    def update_child(self, child_id: str, new_data: dict[str, Any]) -> None:
        """Aktualisiert Felder des Kindes mit der ID child_id."""
        if self.storage_mode == "google":
            sheets_repo.update_child(child_id, new_data)
            return

        children = self._read_local_children()
        for index, child in enumerate(children):
            if child.get("id") == child_id:
                merged_data = {**child, **new_data}
                merged_data["download_consent"] = _normalize_download_consent(
                    merged_data.get("download_consent")
                )
                children[index] = merged_data
                self._write_local_children(children)
                return
        raise KeyError(f"Kind mit ID '{child_id}' wurde nicht gefunden.")

    def delete_child(self, child_id: str) -> None:
        """Löscht den Kind-Datensatz."""
        if self.storage_mode == "google":
            sheets_repo.delete_child(child_id)
            return

        children = self._read_local_children()
        filtered = [child for child in children if child.get("id") != child_id]
        self._write_local_children(filtered)

    def get_pickup_authorizations_by_child_id(
        self,
        child_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Liefert Abholberechtigungen eines Kindes."""
        if self.storage_mode == "google":
            authorizations = sheets_repo.get_pickup_authorizations_by_child_id(child_id)
        else:
            normalized_child_id = child_id.strip()
            authorizations = [
                record
                for record in self._read_local_pickup_authorizations()
                if str(record.get("child_id", "")).strip() == normalized_child_id
            ]

        normalized_authorizations: list[dict[str, Any]] = []
        for authorization in authorizations:
            normalized = {
                key: str(value).strip() for key, value in authorization.items()
            }
            normalized["active"] = (
                str(authorization.get("active", "true")).strip().lower() or "true"
            )
            normalized_authorizations.append(normalized)

        if active_only:
            normalized_authorizations = [
                record
                for record in normalized_authorizations
                if record.get("active", "true") == "true"
            ]

        normalized_authorizations.sort(key=lambda item: item.get("name", ""))
        return normalized_authorizations

    def add_pickup_authorization(
        self,
        child_id: str,
        pickup_data: dict[str, Any],
        *,
        created_by: str,
    ) -> str:
        """Legt eine neue Abholberechtigung an."""
        payload = {
            "child_id": child_id.strip(),
            "name": str(pickup_data.get("name", "")).strip(),
            "relationship": str(pickup_data.get("relationship", "")).strip(),
            "phone": str(pickup_data.get("phone", "")).strip(),
            "valid_from": str(pickup_data.get("valid_from", "")).strip(),
            "valid_to": str(pickup_data.get("valid_to", "")).strip(),
            "active": str(pickup_data.get("active", "true")).strip().lower() or "true",
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "created_by": created_by.strip(),
        }

        if self.storage_mode == "google":
            return sheets_repo.add_pickup_authorization(payload)

        pickup_id = uuid.uuid4().hex
        local_records = self._read_local_pickup_authorizations()
        local_records.append({"pickup_id": pickup_id, **payload})
        self._write_local_pickup_authorizations(local_records)
        return pickup_id

    def update_pickup_authorization(
        self,
        pickup_id: str,
        patch_data: dict[str, Any],
    ) -> None:
        """Aktualisiert eine vorhandene Abholberechtigung."""
        normalized_patch = {
            key: str(value).strip() for key, value in patch_data.items()
        }
        if "active" in normalized_patch:
            normalized_patch["active"] = (
                str(normalized_patch.get("active", "true")).strip().lower() or "true"
            )

        if self.storage_mode == "google":
            sheets_repo.update_pickup_authorization(pickup_id, normalized_patch)
            return

        local_records = self._read_local_pickup_authorizations()
        for index, record in enumerate(local_records):
            if str(record.get("pickup_id", "")).strip() == pickup_id.strip():
                local_records[index] = {**record, **normalized_patch}
                self._write_local_pickup_authorizations(local_records)
                return
        raise KeyError(f"Abholberechtigung mit ID '{pickup_id}' wurde nicht gefunden.")

    def get_medications_by_child_id(self, child_id: str) -> list[dict[str, Any]]:
        """Liefert Medikamenten-Einträge für ein Kind (neueste zuerst)."""
        normalized_child_id = child_id.strip()
        if self.storage_mode == "google":
            medications = sheets_repo.get_medications_by_child_id(normalized_child_id)
        else:
            medications = [
                record
                for record in self._read_local_medications()
                if str(record.get("child_id", "")).strip() == normalized_child_id
            ]

        normalized_records: list[dict[str, Any]] = []
        for medication in medications:
            normalized_records.append(
                {key: str(value).strip() for key, value in medication.items()}
            )

        normalized_records.sort(
            key=lambda item: item.get("date_time", ""),
            reverse=True,
        )
        return normalized_records

    def get_photo_meta_records(self) -> list[dict[str, Any]]:
        """Liefert alle Foto-Metadaten."""
        if self.storage_mode == "google":
            records = sheets_repo.get_photo_meta_records()
        else:
            records = self._read_local_photo_meta()
        return [
            {key: str(value).strip() for key, value in record.items()}
            for record in records
        ]

    def get_photo_meta_by_file_id(self, file_id: str) -> dict[str, Any] | None:
        """Liefert Foto-Metadaten zu einer File-ID."""
        normalized_file_id = file_id.strip()
        if self.storage_mode == "google":
            record = sheets_repo.get_photo_meta_by_file_id(normalized_file_id)
            if not record:
                return None
            return {key: str(value).strip() for key, value in record.items()}

        for record in self._read_local_photo_meta():
            if str(record.get("file_id", "")).strip() == normalized_file_id:
                return {key: str(value).strip() for key, value in record.items()}
        return None

    def upsert_photo_meta(self, file_id: str, patch_data: dict[str, Any]) -> None:
        """Legt Foto-Metadaten an oder aktualisiert bestehende Einträge."""
        normalized_file_id = file_id.strip()
        if not normalized_file_id:
            raise ValueError("file_id ist erforderlich.")

        normalized_patch = {
            key: str(value).strip() for key, value in patch_data.items()
        }

        if self.storage_mode == "google":
            sheets_repo.upsert_photo_meta(normalized_file_id, normalized_patch)
            return

        records = self._read_local_photo_meta()
        for index, record in enumerate(records):
            if str(record.get("file_id", "")).strip() == normalized_file_id:
                merged_record = {
                    **record,
                    **normalized_patch,
                    "file_id": normalized_file_id,
                }
                records[index] = merged_record
                self._write_local_photo_meta(records)
                return

        records.append({"file_id": normalized_file_id, **normalized_patch})
        self._write_local_photo_meta(records)

    def add_medication(
        self,
        child_id: str,
        medication_data: dict[str, Any],
        *,
        created_by: str,
    ) -> str:
        """Legt einen auditierbaren Medikamenten-Eintrag an."""
        payload = {
            "child_id": child_id.strip(),
            "date_time": str(medication_data.get("date_time", "")).strip(),
            "med_name": str(medication_data.get("med_name", "")).strip(),
            "dose": str(medication_data.get("dose", "")).strip(),
            "given_by": str(medication_data.get("given_by", "")).strip(),
            "notes": str(medication_data.get("notes", "")).strip(),
            "consent_doc_file_id": str(
                medication_data.get("consent_doc_file_id", "")
            ).strip(),
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "created_by": created_by.strip(),
        }

        if self.storage_mode == "google":
            return sheets_repo.add_medication(payload)

        med_id = uuid.uuid4().hex
        local_records = self._read_local_medications()
        local_records.append({"med_id": med_id, **payload})
        self._write_local_medications(local_records)
        return med_id
