from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

import pytest


class FakeDriveAgent:
    def __init__(self, files: list[dict[str, Any]] | None = None) -> None:
        self.files = files or []
        self.upload_calls: list[dict[str, Any]] = []
        self.list_calls: list[dict[str, str | None]] = []

    def upload_file(
        self,
        name: str,
        content_bytes: bytes,
        mime_type: str,
        parent_folder_id: str | None,
    ) -> str:
        self.upload_calls.append(
            {
                "name": name,
                "content_bytes": content_bytes,
                "mime_type": mime_type,
                "parent_folder_id": parent_folder_id,
            }
        )
        return "fake-photo-id"

    def list_files(
        self,
        folder_id: str,
        mime_type_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        self.list_calls.append(
            {"folder_id": folder_id, "mime_type_filter": mime_type_filter}
        )
        return self.files


@dataclass(frozen=True)
class FakeUploadedFile:
    name: str
    type: str
    content: bytes

    def getvalue(self) -> bytes:
        return self.content


def _png_bytes() -> bytes:
    image_module = pytest.importorskip("PIL.Image")
    image = image_module.new("RGB", (2, 2), color=(10, 20, 30))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_photo_ui_and_service_imports() -> None:
    from services.photo_share_service import list_child_photos, upload_child_photo
    from ui.photos import render_photo_share_page

    assert callable(render_photo_share_page)
    assert callable(upload_child_photo)
    assert callable(list_child_photos)


def test_photo_service_smoke_with_fake_drive_agent() -> None:
    from services.photo_share_service import list_child_photos, upload_child_photo

    fake_files = [
        {
            "id": "fake-listed-photo-id",
            "name": "listed_photo.png",
            "mimeType": "image/png",
        }
    ]
    drive_agent = FakeDriveAgent(files=fake_files)
    child_record = {"id": "child-smoke", "folder_id": "folder-smoke"}
    uploaded_file = FakeUploadedFile(
        name="upload.png",
        type="image/png",
        content=_png_bytes(),
    )

    upload_result = upload_child_photo(
        drive_agent=drive_agent,
        child_record=child_record,
        uploaded_file=uploaded_file,
        uploaded_by_email="test-uploader",
    )
    listed_photos = list_child_photos(drive_agent, child_record)

    assert upload_result.file_id == "fake-photo-id"
    assert upload_result.folder_id == "folder-smoke"
    assert upload_result.file_name.endswith(".png")
    assert drive_agent.upload_calls == [
        {
            "name": upload_result.file_name,
            "content_bytes": uploaded_file.content,
            "mime_type": "image/png",
            "parent_folder_id": "folder-smoke",
        }
    ]
    assert listed_photos == fake_files
    assert drive_agent.list_calls == [
        {"folder_id": "folder-smoke", "mime_type_filter": "image/"}
    ]
