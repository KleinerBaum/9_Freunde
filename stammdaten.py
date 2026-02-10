from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from config import get_app_config
from services.local_ods_repo import LocalODSRepository
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
        self.stammdaten_file = self.config.local.stammdaten_file
        self.local_ods_repo = LocalODSRepository(self.stammdaten_file)

        if self.storage_mode != "google":
            self._migrate_legacy_json_to_ods()
            self.local_ods_repo.ensure_workbook()

    def _migrate_legacy_json_to_ods(self) -> None:
        if self.stammdaten_file.exists():
            return

        legacy_sources = {
            "children": self.config.local.data_dir / "children.json",
            "parents": self.config.local.data_dir / "parents.json",
            "consents": self.config.local.data_dir / "consents.json",
            "pickup_authorizations": self.config.local.data_dir
            / "pickup_authorizations.json",
            "medications": self.config.local.data_dir / "medications.json",
            "photo_meta": self.config.local.data_dir / "photo_meta.json",
        }

        for sheet_name, source_file in legacy_sources.items():
            records = self._read_legacy_json_records(source_file)
            if records:
                self.local_ods_repo.write_sheet(sheet_name, records)

    @staticmethod
    def _read_legacy_json_records(source_file: Path) -> list[dict[str, Any]]:
        if not source_file.exists():
            return []

        data = json.loads(source_file.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return [record for record in data if isinstance(record, dict)]

    def _read_local_children(self) -> list[dict[str, Any]]:
        return self.local_ods_repo.read_sheet("children")

    def _write_local_children(self, children: list[dict[str, Any]]) -> None:
        self.local_ods_repo.write_sheet("children", children)

    def _read_local_parents(self) -> list[dict[str, Any]]:
        return self.local_ods_repo.read_sheet("parents")

    def _write_local_parents(self, parents: list[dict[str, Any]]) -> None:
        self.local_ods_repo.write_sheet("parents", parents)

    def _read_local_consents(self) -> list[dict[str, Any]]:
        return self.local_ods_repo.read_sheet("consents")

    def _write_local_consents(self, consents: list[dict[str, Any]]) -> None:
        self.local_ods_repo.write_sheet("consents", consents)

    def _read_local_pickup_authorizations(self) -> list[dict[str, Any]]:
        return self.local_ods_repo.read_sheet("pickup_authorizations")

    def _write_local_pickup_authorizations(
        self,
        pickup_authorizations: list[dict[str, Any]],
    ) -> None:
        self.local_ods_repo.write_sheet("pickup_authorizations", pickup_authorizations)

    def _read_local_medications(self) -> list[dict[str, Any]]:
        return self.local_ods_repo.read_sheet("medications")

    def _write_local_medications(self, medications: list[dict[str, Any]]) -> None:
        self.local_ods_repo.write_sheet("medications", medications)

    def _read_local_photo_meta(self) -> list[dict[str, Any]]:
        return self.local_ods_repo.read_sheet("photo_meta")

    def _write_local_photo_meta(self, records: list[dict[str, Any]]) -> None:
        self.local_ods_repo.write_sheet("photo_meta", records)

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

    def add_child(
        self,
        name: str,
        parent_email: str,
        extra_data: dict[str, Any] | None = None,
    ) -> str:
        """Fügt ein Kind hinzu und erstellt optional einen Drive-Ordner."""
        additional_child_data = extra_data or {}
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
            child_data.update(additional_child_data)
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
        child_data.update(additional_child_data)
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

    def get_parents(self) -> list[dict[str, Any]]:
        """Liefert alle Eltern-Datensätze."""
        if self.storage_mode == "google":
            return [
                {key: str(value).strip() for key, value in parent.items()}
                for parent in sheets_repo.get_parents()
            ]

        return [
            {key: str(value).strip() for key, value in parent.items()}
            for parent in self._read_local_parents()
        ]

    def get_parent_by_email(self, email: str) -> dict[str, Any] | None:
        """Liefert einen Eltern-Datensatz über die E-Mail-Adresse."""
        normalized_email = email.strip().lower()
        if not normalized_email:
            return None

        for parent in self.get_parents():
            if str(parent.get("email", "")).strip().lower() == normalized_email:
                return parent
        return None

    def upsert_parent_by_email(self, email: str, parent_data: dict[str, Any]) -> str:
        """Erstellt oder aktualisiert einen Eltern-Datensatz anhand der E-Mail."""
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise ValueError("E-Mail darf nicht leer sein.")

        normalized_parent_data = {
            key: str(value).strip() for key, value in parent_data.items()
        }
        normalized_parent_data["email"] = normalized_email
        normalized_parent_data["notifications_opt_in"] = (
            "true"
            if str(normalized_parent_data.get("notifications_opt_in", "false"))
            .strip()
            .lower()
            == "true"
            else "false"
        )

        existing_parent = self.get_parent_by_email(normalized_email)

        if self.storage_mode == "google":
            if existing_parent:
                parent_id = str(existing_parent.get("parent_id", "")).strip()
                if not parent_id:
                    raise KeyError(
                        f"Eltern-Datensatz für '{normalized_email}' enthält keine parent_id."
                    )
                sheets_repo.update_parent(parent_id, normalized_parent_data)
                return parent_id
            return sheets_repo.add_parent(normalized_parent_data)

        parents = self._read_local_parents()
        if existing_parent:
            parent_id = str(existing_parent.get("parent_id", "")).strip()
            for index, parent in enumerate(parents):
                if str(parent.get("parent_id", "")).strip() == parent_id:
                    parents[index] = {**parent, **normalized_parent_data}
                    self._write_local_parents(parents)
                    return parent_id

        parent_id = uuid.uuid4().hex
        parents.append({"parent_id": parent_id, **normalized_parent_data})
        self._write_local_parents(parents)
        return parent_id

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
