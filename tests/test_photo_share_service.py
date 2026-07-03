from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

import pytest

from services.photo_share_service import (
    MAX_PHOTO_BYTES,
    PhotoShareError,
    PhotoUploadResult,
    list_child_photos,
    upload_child_photo,
)


class FakeDriveAgent:
    def __init__(self, files: list[dict[str, Any]] | None = None) -> None:
        self.files = files or []
        self.upload_calls: list[dict[str, Any]] = []
        self.list_calls: list[dict[str, str | None]] = []

    def upload_file(
        self,
        filename: str,
        file_bytes: bytes,
        mime_type: str,
        folder_id: str,
    ) -> str:
        self.upload_calls.append(
            {
                "filename": filename,
                "file_bytes": file_bytes,
                "mime_type": mime_type,
                "folder_id": folder_id,
            }
        )
        return "fake-file-id"

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


def _image_bytes(image_format: str) -> bytes:
    image_module = pytest.importorskip("PIL.Image")
    image = image_module.new("RGB", (2, 2), color=(10, 20, 30))
    buffer = BytesIO()

    try:
        image.save(buffer, format=image_format)
    except OSError as exc:
        pytest.skip(f"Pillow does not support {image_format}: {exc}")

    return buffer.getvalue()


def _upload(
    uploaded_file: FakeUploadedFile,
    *,
    child_record: dict[str, Any] | None = None,
    uploaded_by_email: str = "uploader@example.org",
) -> tuple[PhotoUploadResult, FakeDriveAgent]:
    drive_agent = FakeDriveAgent()
    result = upload_child_photo(
        drive_agent=drive_agent,
        child_record=child_record or {"id": "child-123", "folder_id": "folder-123"},
        uploaded_file=uploaded_file,
        uploaded_by_email=uploaded_by_email,
    )
    return result, drive_agent


def test_valid_jpeg_upload_returns_photo_upload_result() -> None:
    uploaded_file = FakeUploadedFile(
        name="playground.jpg",
        type="image/jpeg",
        content=_image_bytes("JPEG"),
    )

    result, drive_agent = _upload(uploaded_file)

    assert isinstance(result, PhotoUploadResult)
    assert result.file_id == "fake-file-id"
    assert result.folder_id == "folder-123"
    assert result.file_name.endswith(".jpg")
    assert drive_agent.upload_calls[0]["mime_type"] == "image/jpeg"


def test_valid_png_upload_returns_photo_upload_result() -> None:
    uploaded_file = FakeUploadedFile(
        name="playground.png",
        type="image/png",
        content=_image_bytes("PNG"),
    )

    result, drive_agent = _upload(uploaded_file)

    assert isinstance(result, PhotoUploadResult)
    assert result.file_id == "fake-file-id"
    assert result.file_name.endswith(".png")
    assert drive_agent.upload_calls[0]["mime_type"] == "image/png"


def test_valid_webp_upload_returns_photo_upload_result() -> None:
    uploaded_file = FakeUploadedFile(
        name="playground.webp",
        type="image/webp",
        content=_image_bytes("WEBP"),
    )

    result, drive_agent = _upload(uploaded_file)

    assert isinstance(result, PhotoUploadResult)
    assert result.file_id == "fake-file-id"
    assert result.file_name.endswith(".webp")
    assert drive_agent.upload_calls[0]["mime_type"] == "image/webp"


def test_missing_folder_id_raises_photo_share_error() -> None:
    uploaded_file = FakeUploadedFile(
        name="playground.jpg",
        type="image/jpeg",
        content=b"not read before folder validation",
    )

    with pytest.raises(PhotoShareError):
        upload_child_photo(
            drive_agent=FakeDriveAgent(),
            child_record={"id": "child-123"},
            uploaded_file=uploaded_file,
            uploaded_by_email="uploader@example.org",
        )


def test_text_file_renamed_to_jpg_raises_photo_share_error() -> None:
    uploaded_file = FakeUploadedFile(
        name="notes.jpg",
        type="image/jpeg",
        content=b"This is not image data.",
    )

    with pytest.raises(PhotoShareError):
        upload_child_photo(
            drive_agent=FakeDriveAgent(),
            child_record={"id": "child-123", "folder_id": "folder-123"},
            uploaded_file=uploaded_file,
            uploaded_by_email="uploader@example.org",
        )


def test_unsupported_extension_and_mime_raises_photo_share_error() -> None:
    uploaded_file = FakeUploadedFile(
        name="notes.txt",
        type="text/plain",
        content=b"plain text",
    )

    with pytest.raises(PhotoShareError):
        upload_child_photo(
            drive_agent=FakeDriveAgent(),
            child_record={"id": "child-123", "folder_id": "folder-123"},
            uploaded_file=uploaded_file,
            uploaded_by_email="uploader@example.org",
        )


def test_file_larger_than_max_photo_bytes_raises_photo_share_error() -> None:
    uploaded_file = FakeUploadedFile(
        name="large.jpg",
        type="image/jpeg",
        content=b"x" * (MAX_PHOTO_BYTES + 1),
    )

    with pytest.raises(PhotoShareError):
        upload_child_photo(
            drive_agent=FakeDriveAgent(),
            child_record={"id": "child-123", "folder_id": "folder-123"},
            uploaded_file=uploaded_file,
            uploaded_by_email="uploader@example.org",
        )


def test_filename_does_not_contain_uploader_email() -> None:
    uploaded_file = FakeUploadedFile(
        name="../playground photo.jpg",
        type="image/jpeg",
        content=_image_bytes("JPEG"),
    )

    result, drive_agent = _upload(
        uploaded_file,
        uploaded_by_email="parent@example.org",
    )

    uploaded_name = drive_agent.upload_calls[0]["filename"]
    assert uploaded_name == result.file_name
    assert "parent@example.org" not in result.file_name
    assert "/" not in result.file_name
    assert "\\" not in result.file_name
    assert " " not in result.file_name


@pytest.mark.parametrize(
    ("child_record", "expected_child_id"),
    [
        ({"id": "child-main", "folder_id": "folder-123"}, "child-main"),
        ({"child_id": "child-fallback", "folder_id": "folder-123"}, "child-fallback"),
    ],
)
def test_filename_contains_child_id_or_child_id_fallback(
    child_record: dict[str, Any],
    expected_child_id: str,
) -> None:
    uploaded_file = FakeUploadedFile(
        name="playground.png",
        type="image/png",
        content=_image_bytes("PNG"),
    )

    result, _drive_agent = _upload(uploaded_file, child_record=child_record)

    assert expected_child_id in result.file_name


def test_list_child_photos_returns_empty_list_when_folder_id_missing() -> None:
    drive_agent = FakeDriveAgent(files=[{"id": "photo-1"}])

    photos = list_child_photos(drive_agent, {"id": "child-123"})

    assert photos == []
    assert drive_agent.list_calls == []


def test_list_child_photos_calls_fake_agent_with_image_mime_filter() -> None:
    expected_files = [{"id": "photo-1", "name": "playground.jpg"}]
    drive_agent = FakeDriveAgent(files=expected_files)

    photos = list_child_photos(
        drive_agent,
        {"id": "child-123", "folder_id": "folder-123"},
    )

    assert photos == expected_files
    assert drive_agent.list_calls == [
        {"folder_id": "folder-123", "mime_type_filter": "image/"}
    ]
