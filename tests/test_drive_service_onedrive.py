from __future__ import annotations

from typing import Any

import pytest

from services import drive_service


class _DummyResponse:
    def __init__(
        self, payload: dict[str, Any] | None = None, content: bytes = b""
    ) -> None:
        self._payload = payload or {}
        self.content = content

    def json(self) -> dict[str, Any]:
        return self._payload


class _DummyClient:
    def __init__(self) -> None:
        self.drive_base_path = "/users/user-11/drive"
        self.calls: list[tuple[str, str, dict[str, str] | None, bytes | None]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> _DummyResponse:
        del params
        self.calls.append((method, path, headers, data))

        if method == "POST" and path.endswith("/children"):
            return _DummyResponse({"id": "created-folder"})
        if method == "PUT" and path.endswith(":/content"):
            return _DummyResponse({"id": "uploaded-file"})
        if method == "GET" and path.endswith("/children"):
            return _DummyResponse(
                {
                    "value": [
                        {
                            "id": "f-1",
                            "name": "bild.jpg",
                            "file": {"mimeType": "image/jpeg"},
                            "lastModifiedDateTime": "2026-01-01T08:00:00Z",
                        },
                        {
                            "id": "f-2",
                            "name": "doc.pdf",
                            "file": {"mimeType": "application/pdf"},
                            "lastModifiedDateTime": "2026-01-01T07:00:00Z",
                        },
                    ]
                }
            )
        if method == "GET" and path.endswith("/content"):
            return _DummyResponse(content=b"binary")
        return _DummyResponse({})


def test_upload_and_download_use_onedrive_graph_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _DummyClient()
    monkeypatch.setattr(
        drive_service.st,
        "secrets",
        {"onedrive": {"enabled": True, "folder_path": "Documents/9 Freunde"}},
    )
    monkeypatch.setattr(drive_service, "get_graph_client", lambda: client)

    uploaded_id = drive_service.upload_bytes_to_folder(
        "folder-55",
        "test.jpg",
        b"img",
        "image/jpeg",
    )
    downloaded = drive_service.download_file("item-77")

    assert uploaded_id == "uploaded-file"
    assert downloaded == b"binary"
    assert (
        client.calls[0][1] == "/users/user-11/drive/items/folder-55:/test.jpg:/content"
    )
    assert client.calls[1][1] == "/users/user-11/drive/items/item-77/content"


def test_list_files_in_folder_filters_mime_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _DummyClient()
    monkeypatch.setattr(drive_service.st, "secrets", {"onedrive": {"enabled": True}})
    monkeypatch.setattr(drive_service, "get_graph_client", lambda: client)

    files = drive_service.list_files_in_folder("folder-11", mime_type_filter="image/")

    assert files == [
        {
            "id": "f-1",
            "name": "bild.jpg",
            "mimeType": "image/jpeg",
            "modifiedTime": "2026-01-01T08:00:00Z",
        }
    ]


def test_create_folder_uses_onedrive_children_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _DummyClient()
    monkeypatch.setattr(drive_service.st, "secrets", {"onedrive": {"enabled": True}})
    monkeypatch.setattr(drive_service, "get_graph_client", lambda: client)

    folder_id = drive_service.create_folder("Neu", parent_id="parent-8")

    assert folder_id == "created-folder"
    assert client.calls[0][0] == "POST"
    assert client.calls[0][1] == "/users/user-11/drive/items/parent-8/children"
