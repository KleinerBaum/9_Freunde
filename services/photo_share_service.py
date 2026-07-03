from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any, Protocol

try:
    from PIL import Image as PILImage
    from PIL import UnidentifiedImageError
except ImportError:
    PILImage = None

    class UnidentifiedImageError(OSError):
        pass

ALLOWED_IMAGE_MIME_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
ALLOWED_EXTENSIONS: set[str] = {"jpg", "jpeg", "png", "webp"}
MAX_PHOTO_BYTES = 15 * 1024 * 1024

_EXTENSION_TO_MIME_TYPE: dict[str, str] = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}
_PIL_FORMAT_TO_MIME_TYPE: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
_SAFE_FILENAME_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]+")


class PhotoShareError(RuntimeError):
    """Domain error for child photo upload and listing."""


@dataclass(frozen=True, slots=True)
class PhotoUploadResult:
    file_id: str
    file_name: str
    folder_id: str


class _DriveAgent(Protocol):
    def list_files(
        self, folder_id: str, mime_type_filter: str | None = None
    ) -> list[dict[str, Any]]: ...

    def upload_file(
        self,
        name: str,
        content_bytes: bytes,
        mime_type: str,
        parent_folder_id: str | None,
    ) -> str | None: ...


def child_id_from_record(child_record: dict[str, Any]) -> str:
    """Return the normalized child id, preferring `id` over `child_id`."""
    child_id = str(child_record.get("id") or "").strip()
    if child_id:
        return child_id
    return str(child_record.get("child_id") or "").strip()


def _safe_component(value: str, *, fallback: str, max_length: int = 80) -> str:
    normalized = _SAFE_FILENAME_CHARS_RE.sub("_", value.strip())
    normalized = normalized.strip("._-")
    if not normalized:
        normalized = fallback
    return normalized[:max_length].strip("._-") or fallback


def _original_basename(original_file_name: str) -> str:
    normalized_path = original_file_name.replace("\\", "/")
    file_name = PurePosixPath(normalized_path).name
    if not file_name:
        return "photo"
    if "." not in file_name:
        return file_name
    return ".".join(file_name.split(".")[:-1]) or "photo"


def build_photo_filename(
    *,
    original_file_name: str,
    mime_type: str,
    child_id: str | None = None,
    uploaded_by_email: str = "",
    timestamp: datetime | None = None,
) -> str:
    """Build a sanitized, non-PII photo filename for Drive storage."""
    normalized_mime_type = mime_type.strip().lower()
    extension = ALLOWED_IMAGE_MIME_TYPES.get(normalized_mime_type)
    if extension is None:
        raise PhotoShareError("Unsupported image type.")

    timestamp_value = timestamp or datetime.now(timezone.utc)
    if timestamp_value.tzinfo is None:
        timestamp_value = timestamp_value.replace(tzinfo=timezone.utc)
    timestamp_part = timestamp_value.astimezone(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    child_part = _safe_component(child_id or "", fallback="child", max_length=48)
    email_hash = hashlib.sha256(
        uploaded_by_email.strip().lower().encode("utf-8")
    ).hexdigest()[:10]
    original_part = _safe_component(
        _original_basename(original_file_name),
        fallback="photo",
        max_length=80,
    )

    return f"{timestamp_part}_{child_part}_{email_hash}_{original_part}.{extension}"


def list_child_photos(
    drive_agent: _DriveAgent,
    child_record: dict[str, Any],
) -> list[dict[str, Any]]:
    folder_id = str(child_record.get("folder_id") or "").strip()
    if not folder_id:
        return []
    return drive_agent.list_files(folder_id, mime_type_filter="image/")


def _uploaded_file_name(uploaded_file: Any) -> str:
    return str(getattr(uploaded_file, "name", "") or "").strip() or "photo"


def _mime_type_from_upload(uploaded_file: Any) -> str:
    uploaded_mime_type = str(getattr(uploaded_file, "type", "") or "").strip().lower()
    if uploaded_mime_type in ALLOWED_IMAGE_MIME_TYPES:
        return uploaded_mime_type

    original_file_name = _uploaded_file_name(uploaded_file)
    extension = original_file_name.rsplit(".", maxsplit=1)[-1].strip().lower()
    if extension in ALLOWED_EXTENSIONS:
        return _EXTENSION_TO_MIME_TYPE[extension]

    raise PhotoShareError("Only JPG, PNG, and WebP images are allowed.")


def _read_uploaded_file_bytes(uploaded_file: Any) -> bytes:
    getvalue = getattr(uploaded_file, "getvalue", None)
    if not callable(getvalue):
        raise PhotoShareError("Upload is invalid.")

    try:
        file_bytes = getvalue()
    except Exception as exc:
        raise PhotoShareError("Upload could not be read.") from exc

    if not isinstance(file_bytes, bytes):
        raise PhotoShareError("Upload is invalid.")
    if not file_bytes:
        raise PhotoShareError("Image file is empty.")
    if len(file_bytes) > MAX_PHOTO_BYTES:
        raise PhotoShareError("Image file is larger than 15 MB.")
    return file_bytes


def _verify_image_bytes(file_bytes: bytes, expected_mime_type: str) -> None:
    if PILImage is None:
        raise PhotoShareError("Pillow is required for image validation.")

    try:
        with PILImage.open(BytesIO(file_bytes)) as image:
            detected_mime_type = _PIL_FORMAT_TO_MIME_TYPE.get(image.format or "")
            if detected_mime_type != expected_mime_type:
                raise PhotoShareError("Image content does not match the file type.")
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise PhotoShareError("Upload is not a valid image file.") from exc


def upload_child_photo(
    *,
    drive_agent: _DriveAgent,
    child_record: dict[str, Any],
    uploaded_file: Any,
    uploaded_by_email: str,
) -> PhotoUploadResult:
    folder_id = str(child_record.get("folder_id") or "").strip()
    if not folder_id:
        raise PhotoShareError("Drive target folder is missing.")

    mime_type = _mime_type_from_upload(uploaded_file)
    file_bytes = _read_uploaded_file_bytes(uploaded_file)
    _verify_image_bytes(file_bytes, mime_type)

    file_name = build_photo_filename(
        original_file_name=_uploaded_file_name(uploaded_file),
        mime_type=mime_type,
        child_id=child_id_from_record(child_record),
        uploaded_by_email=uploaded_by_email,
    )

    try:
        file_id = drive_agent.upload_file(file_name, file_bytes, mime_type, folder_id)
    except Exception as exc:
        raise PhotoShareError("Photo upload failed.") from exc

    normalized_file_id = str(file_id or "").strip()
    if not normalized_file_id:
        raise PhotoShareError("Photo upload returned no file id.")

    return PhotoUploadResult(
        file_id=normalized_file_id,
        file_name=file_name,
        folder_id=folder_id,
    )
