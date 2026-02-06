from enum import Enum

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
