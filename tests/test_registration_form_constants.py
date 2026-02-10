from __future__ import annotations

from PyPDF2 import PdfReader

from constants import (
    REGISTRATION_FORM_SCHEMA_VERSION,
    REGISTRATION_FORM_TEMPLATE_FILENAME,
    REGISTRATION_FORM_TEMPLATE_PATH,
    REGISTRATION_PAYLOAD_KEYS_V1,
    REGISTRATION_PDF_FIELDS_V1,
    REGISTRATION_REQUIRED_FIELDS_V1,
    REGISTRATION_UI_KEYS_V1,
    get_registration_pdf_template_bytes,
)


def test_registration_schema_version_and_template_name() -> None:
    assert REGISTRATION_FORM_SCHEMA_VERSION == "v1"
    assert REGISTRATION_FORM_TEMPLATE_FILENAME == "9Freunde_Anmeldeformular_v1.pdf"
    assert REGISTRATION_FORM_TEMPLATE_PATH.exists()


def test_registration_pdf_fields_match_template() -> None:
    reader = PdfReader(str(REGISTRATION_FORM_TEMPLATE_PATH))
    pdf_fields = list((reader.get_fields() or {}).keys())

    assert REGISTRATION_PDF_FIELDS_V1 == pdf_fields


def test_required_fields_are_subset_of_pdf_fields() -> None:
    assert set(REGISTRATION_REQUIRED_FIELDS_V1).issubset(
        set(REGISTRATION_PDF_FIELDS_V1)
    )


def test_ui_and_payload_keys_are_centralized_for_each_field() -> None:
    expected_fields = set(REGISTRATION_PDF_FIELDS_V1)

    assert set(REGISTRATION_UI_KEYS_V1.keys()) == expected_fields
    assert set(REGISTRATION_PAYLOAD_KEYS_V1.keys()) == expected_fields
    assert set(REGISTRATION_UI_KEYS_V1.values()) == {
        f"registration_{field_name}" for field_name in expected_fields
    }
    assert set(REGISTRATION_PAYLOAD_KEYS_V1.values()) == expected_fields


def test_get_registration_pdf_template_bytes_returns_pdf_bytes() -> None:
    template_bytes = get_registration_pdf_template_bytes()

    assert isinstance(template_bytes, bytes)
    assert len(template_bytes) > 0
    assert template_bytes.startswith(b"%PDF")
