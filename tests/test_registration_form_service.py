from __future__ import annotations

from io import BytesIO
from typing import Any

import pytest

from services import registration_form_service as service


class _FakePdfReader:
    def __init__(self, stream: BytesIO) -> None:
        assert isinstance(stream, BytesIO)

    def get_fields(self) -> dict[str, dict[str, Any]]:
        return {
            "meta__schema_version": {"/V": " v1 "},
            "child__name": {"/V": "  Max   Mustermann "},
            "consent__privacy_notice_ack": {"/V": "/Yes"},
            "consent__photo_download_denied": {"/V": "/Off"},
        }


class _FakePdfReaderNoFields:
    def __init__(self, stream: BytesIO) -> None:
        assert isinstance(stream, BytesIO)

    def get_fields(self) -> dict[str, dict[str, Any]]:
        return {}


class _FakePdfReaderBadSchema:
    def __init__(self, stream: BytesIO) -> None:
        assert isinstance(stream, BytesIO)

    def get_fields(self) -> dict[str, dict[str, Any]]:
        return {
            "meta__schema_version": {"/V": "v2"},
            "child__name": {"/V": "Test"},
        }


def test_extract_acroform_fields_normalizes_strings_and_checkboxes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "PdfReader", _FakePdfReader)

    fields = service.extract_acroform_fields(b"%PDF-1.4")

    assert fields["meta__schema_version"] == "v1"
    assert fields["child__name"] == "Max Mustermann"
    assert fields["consent__privacy_notice_ack"] is True
    assert fields["consent__photo_download_denied"] is False


def test_extract_acroform_fields_raises_when_no_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "PdfReader", _FakePdfReaderNoFields)

    with pytest.raises(ValueError, match="keine auslesbaren Felder"):
        service.extract_acroform_fields(b"%PDF-1.4")


def test_extract_acroform_fields_raises_for_unsupported_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "PdfReader", _FakePdfReaderBadSchema)

    with pytest.raises(ValueError, match="nicht unterstützt"):
        service.extract_acroform_fields(b"%PDF-1.4")


def test_parse_registration_payload_returns_structured_output() -> None:
    fields: dict[str, Any] = {
        "meta__schema_version": "v1",
        "child__name": "Max Mustermann",
        "child__birthdate": "2020-01-01",
        "child__pickup_password": "1234",
        "parent1__email": "mama@example.org",
        "parent1__name": "Erika Muster",
        "parent1__phone": "+49 123 456",
        "parent1__address": "Musterweg 1",
        "parent1__emergency_contact_name": "Oma",
        "parent1__emergency_contact_phone": "+49 987 654",
        "parent2__name": "Max Muster",
        "pa1__enabled": True,
        "pa1__name": "Tante Lisa",
        "consent__privacy_notice_ack": True,
    }

    payload = service.parse_registration_payload(fields)

    assert payload.child["name"] == "Max Mustermann"
    assert len(payload.parents) == 2
    assert payload.parents[0]["role"] == "parent1"
    assert payload.pickup_authorizations[0]["slot"] == 1
    assert payload.consents["privacy_notice_ack"] is True
    assert payload.meta["schema_version"] == "v1"
    assert payload.errors == []


def test_parse_registration_payload_collects_validation_errors() -> None:
    payload = service.parse_registration_payload({"consent__privacy_notice_ack": False})

    assert "Pflichtfeld fehlt: child__name" in payload.errors
    assert any("consent__privacy_notice_ack" in error for error in payload.errors)
