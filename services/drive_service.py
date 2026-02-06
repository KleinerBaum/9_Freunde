from __future__ import annotations
from io import BytesIO
from typing import Optional, Dict, Any, List

from googleapiclient.http import MediaIoBaseUpload
from services.google_clients import get_drive_client

def upload_bytes_to_folder(
    *,
    folder_id: str,
    filename: str,
    content: bytes,
    mime_type: str,
) -> str:
    drive = get_drive_client()
    media = MediaIoBaseUpload(BytesIO(content), mimetype=mime_type, resumable=False)

    metadata: Dict[str, Any] = {
        "name": filename,
        "parents": [folder_id],
    }

    created = drive.files().create(
        body=metadata,
        media_body=media,
        fields="id, name",
        supportsAllDrives=True,
    ).execute()

    return created["id"]

def list_files_in_folder(folder_id: str, *, q_extra: Optional[str] = None) -> List[Dict[str, Any]]:
    drive = get_drive_client()
    q = f"'{folder_id}' in parents and trashed = false"
    if q_extra:
        q = f"{q} and ({q_extra})"

    res = drive.files().list(
        q=q,
        fields="files(id, name, mimeType, modifiedTime)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        pageSize=1000,
    ).execute()
    return res.get("files", [])
