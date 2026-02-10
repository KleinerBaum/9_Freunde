from enum import Enum

from constants_forms import (
    REGISTRATION_FORM_SCHEMA_VERSION,
    REGISTRATION_FORM_TEMPLATE_FILENAME,
    REGISTRATION_FORM_TEMPLATE_PATH,
    REGISTRATION_PAYLOAD_KEYS_V1,
    REGISTRATION_PDF_FIELDS_V1,
    REGISTRATION_REQUIRED_FIELDS_V1,
    REGISTRATION_UI_KEYS_V1,
    get_registration_pdf_template_bytes,
)

__all__ = [
    "Role",
    "SecretKeys",
    "GcpSecretFields",
    "REGISTRATION_FORM_SCHEMA_VERSION",
    "REGISTRATION_FORM_TEMPLATE_FILENAME",
    "REGISTRATION_FORM_TEMPLATE_PATH",
    "REGISTRATION_PDF_FIELDS_V1",
    "REGISTRATION_REQUIRED_FIELDS_V1",
    "REGISTRATION_UI_KEYS_V1",
    "REGISTRATION_PAYLOAD_KEYS_V1",
    "get_registration_pdf_template_bytes",
]


class Role(str, Enum):
    ADMIN = "admin"
    PARENT = "parent"


class SecretKeys:
    GCP = "gcp"
    GCP_SA = "gcp_service_account"


class GcpSecretFields:
    PHOTOS_ROOT = "drive_photos_root_folder_id"
    CONTRACTS_FOLDER = "drive_contracts_folder_id"
    STAMMDATEN_SHEET = "stammdaten_sheet_id"
