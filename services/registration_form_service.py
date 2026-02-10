from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from PyPDF2 import PdfReader

from constants import REGISTRATION_FORM_SCHEMA_VERSION

_CHECKBOX_TRUE_VALUES = {"/Yes", "Yes", "true", "True"}
_CHECKBOX_FALSE_VALUES = {"/Off", "Off", "None", "/None"}
_REQUIRED_REGISTRATION_FIELDS = [
    "child__name",
    "child__birthdate",
    "child__pickup_password",
    "parent1__email",
    "parent1__name",
    "parent1__phone",
    "parent1__address",
    "parent1__emergency_contact_name",
    "parent1__emergency_contact_phone",
    "consent__privacy_notice_ack",
]


@dataclass(slots=True)
class RegistrationPayload:
    child: dict[str, Any]
    parents: list[dict[str, Any]]
    pickup_authorizations: list[dict[str, Any]]
    consents: dict[str, Any]
    meta: dict[str, Any]
    errors: list[str] = field(default_factory=list)


def _normalize_string(value: str) -> str:
    return " ".join(value.split())


def _normalize_field_value(value: Any) -> Any:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    if isinstance(value, str):
        normalized = _normalize_string(value)
        if normalized in _CHECKBOX_TRUE_VALUES:
            return True
        if normalized in _CHECKBOX_FALSE_VALUES:
            return False
        return normalized

    return value


def extract_acroform_fields(pdf_bytes: bytes) -> dict[str, Any]:
    reader = PdfReader(BytesIO(pdf_bytes))
    raw_fields = reader.get_fields() or {}
    if not raw_fields:
        raise ValueError("ACROForm enthält keine auslesbaren Felder.")

    normalized_fields: dict[str, Any] = {}
    for field_name, field_definition in raw_fields.items():
        if not isinstance(field_name, str):
            continue

        field_value: Any
        if isinstance(field_definition, dict):
            field_value = field_definition.get("/V")
        else:
            field_value = field_definition

        if field_value is None:
            continue

        normalized_fields[field_name] = _normalize_field_value(field_value)

    schema_version_value = normalized_fields.get("meta__schema_version")
    if not isinstance(schema_version_value, str) or not schema_version_value:
        raise ValueError(
            "Registrierungsformular ist ungültig: schema_version fehlt (meta__schema_version)."
        )

    if schema_version_value != REGISTRATION_FORM_SCHEMA_VERSION:
        raise ValueError(
            "Registrierungsformular ist ungültig: schema_version wird nicht unterstützt "
            f"({schema_version_value!r})."
        )

    return normalized_fields


def _collect_prefix(fields: dict[str, Any], prefix: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    prefix_with_sep = f"{prefix}__"
    for key, value in fields.items():
        if key.startswith(prefix_with_sep):
            result[key.removeprefix(prefix_with_sep)] = value
    return result


def parse_registration_payload(fields: dict[str, Any]) -> RegistrationPayload:
    child = _collect_prefix(fields, "child")
    consents = _collect_prefix(fields, "consent")
    meta = _collect_prefix(fields, "meta")

    parents: list[dict[str, Any]] = []
    for parent_prefix in ("parent1", "parent2"):
        parent_data = _collect_prefix(fields, parent_prefix)
        if parent_data:
            parent_data["role"] = parent_prefix
            parents.append(parent_data)

    pickup_authorizations: list[dict[str, Any]] = []
    for pickup_index in range(1, 5):
        pickup_prefix = f"pa{pickup_index}"
        pickup_data = _collect_prefix(fields, pickup_prefix)
        if not pickup_data:
            continue

        if pickup_data.get("enabled") is True:
            pickup_data["slot"] = pickup_index
            pickup_authorizations.append(pickup_data)
            continue

        has_identity = bool(pickup_data.get("name") or pickup_data.get("phone"))
        if has_identity:
            pickup_data["slot"] = pickup_index
            pickup_authorizations.append(pickup_data)

    errors: list[str] = []
    for required_field in _REQUIRED_REGISTRATION_FIELDS:
        value = fields.get(required_field)
        if required_field == "consent__privacy_notice_ack":
            if value is not True:
                errors.append(
                    "Pflichtfeld fehlt oder ungültig: consent__privacy_notice_ack muss aktiviert sein."
                )
            continue

        if value is None:
            errors.append(f"Pflichtfeld fehlt: {required_field}")
            continue

        if isinstance(value, str) and not value.strip():
            errors.append(f"Pflichtfeld fehlt: {required_field}")

    return RegistrationPayload(
        child=child,
        parents=parents,
        pickup_authorizations=pickup_authorizations,
        consents=consents,
        meta=meta,
        errors=errors,
    )
