from __future__ import annotations

from pathlib import Path

REGISTRATION_FORM_SCHEMA_VERSION = "v1"
REGISTRATION_FORM_TEMPLATE_FILENAME = (
    f"9Freunde_Anmeldeformular_{REGISTRATION_FORM_SCHEMA_VERSION}.pdf"
)
REGISTRATION_FORM_TEMPLATE_PATH = (
    Path(__file__).resolve().parent
    / "assets"
    / "forms"
    / REGISTRATION_FORM_TEMPLATE_FILENAME
)

REGISTRATION_PDF_FIELDS_V1: list[str] = [
    "meta__schema_version",
    "meta__created_on",
    "child__child_id",
    "child__status",
    "child__name",
    "child__birthdate",
    "child__start_date",
    "child__group",
    "child__primary_caregiver",
    "child__pickup_password",
    "child__allergies",
    "child__notes_parent_visible",
    "child__notes_internal",
    "parent1__name",
    "parent1__email",
    "parent1__phone",
    "parent1__phone2",
    "parent1__address",
    "parent1__preferred_language",
    "parent1__notifications_opt_in",
    "parent2__name",
    "parent2__email",
    "parent2__phone",
    "parent2__phone2",
    "parent2__address",
    "parent2__preferred_language",
    "parent2__notifications_opt_in",
    "parent1__emergency_contact_name",
    "parent1__emergency_contact_phone",
    "pa1__enabled",
    "pa1__name",
    "pa1__relation",
    "pa1__phone",
    "pa1__note",
    "pa2__enabled",
    "pa2__name",
    "pa2__relation",
    "pa2__phone",
    "pa2__note",
    "pa3__enabled",
    "pa3__name",
    "pa3__relation",
    "pa3__phone",
    "pa3__note",
    "pa4__enabled",
    "pa4__name",
    "pa4__relation",
    "pa4__phone",
    "pa4__note",
    "child__doctor_name",
    "child__doctor_phone",
    "child__health_insurance",
    "child__medication_regular",
    "child__dietary",
    "child__languages_at_home",
    "child__sleep_habits",
    "child__care_notes_optional",
    "consent__privacy_notice_ack",
    "consent__photo_download_pixelated",
    "consent__photo_download_unpixelated",
    "consent__photo_download_denied",
    "consent__excursions",
    "consent__emergency_treatment",
    "consent__whatsapp_group",
    "sign__place_date",
    "sign__parent1_name",
    "sign__parent2_name",
]

REGISTRATION_REQUIRED_FIELDS_V1: list[str] = [
    "meta__schema_version",
    "child__name",
    "child__birthdate",
    "child__start_date",
    "parent1__name",
    "parent1__email",
    "consent__privacy_notice_ack",
    "sign__place_date",
    "sign__parent1_name",
]

# Canonical mappings for UI state keys and payload keys.
REGISTRATION_UI_KEYS_V1: dict[str, str] = {
    field_name: f"registration_{field_name}"
    for field_name in REGISTRATION_PDF_FIELDS_V1
}
REGISTRATION_PAYLOAD_KEYS_V1: dict[str, str] = {
    field_name: field_name for field_name in REGISTRATION_PDF_FIELDS_V1
}


def get_registration_pdf_template_bytes() -> bytes:
    """Return the canonical registration PDF template as bytes."""
    return REGISTRATION_FORM_TEMPLATE_PATH.read_bytes()
