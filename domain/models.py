from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(slots=True)
class Child:
    id: str
    name: str
    display_name: str | None = None
    group: str | None = None
    parent_emails: list[str] = field(default_factory=list)
    photo_folder_id: str | None = None

    @property
    def label(self) -> str:
        return self.display_name or self.name


@dataclass(slots=True)
class MediaItem:
    id: str
    child_id: str
    name: str
    mime_type: str
    kind: Literal["image", "video"]
    source: Literal["google", "local"]
    created_time: str | None = None
    modified_time: str | None = None
    thumb_bytes: bytes | None = None
    preview_bytes: bytes | None = None
    preview_url: str | None = None

    @property
    def is_video(self) -> bool:
        return self.kind == "video" or self.mime_type.startswith("video/")

    @property
    def is_image(self) -> bool:
        return self.kind == "image" or self.mime_type.startswith("image/")

    @property
    def ext(self) -> str:
        return Path(self.name).suffix.lower()
