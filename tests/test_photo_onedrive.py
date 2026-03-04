from __future__ import annotations

import photo


class _DummyResponse:
    def __init__(self, payload: dict | None = None, content: bytes = b"") -> None:
        self._payload = payload or {}
        self.content = content

    def json(self) -> dict:
        return self._payload


class _DummyClient:
    def __init__(self, drive_base_path: str = "/users/user-42/drive") -> None:
        self.drive_base_path = drive_base_path
        self.calls: list[tuple[str, str, dict | None, bytes | None]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
        data: bytes | None = None,
    ) -> _DummyResponse:
        self.calls.append((method, path, headers, data))
        if path.endswith("/children"):
            return _DummyResponse(
                {
                    "value": [
                        {"id": "1", "name": "bild.jpg"},
                        {"id": "2", "name": "notiz.txt"},
                        {"id": "3", "name": "icon.PNG"},
                    ]
                }
            )
        if path.endswith(":/content") and method == "PUT":
            return _DummyResponse({"id": "new-id", "name": "upload.jpg"})
        return _DummyResponse(content=b"binary-image")


def test_resolve_onedrive_folder_url_uses_configured_url(monkeypatch) -> None:
    monkeypatch.setattr(
        photo.st,
        "secrets",
        {"onedrive": {"shared_folder_url": "https://example.com/share"}},
    )

    resolved = photo._resolve_onedrive_folder_url()

    assert resolved == "https://example.com/share"


def test_resolve_onedrive_folder_url_uses_default_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(photo.st, "secrets", {})

    resolved = photo._resolve_onedrive_folder_url()

    assert resolved == photo.DEFAULT_ONEDRIVE_SHARED_FOLDER_URL


def test_list_photos_from_onedrive_filters_image_extensions(monkeypatch) -> None:
    dummy_client = _DummyClient()
    monkeypatch.setattr(photo, "get_graph_client", lambda: dummy_client)
    monkeypatch.setattr(
        photo,
        "get_onedrive_folder",
        lambda _path: type("Folder", (), {"id": "folder-123"})(),
    )
    monkeypatch.setattr(
        photo.st, "secrets", {"onedrive": {"folder_path": "Documents/9 Freunde"}}
    )

    photos = photo.list_photos_from_onedrive()

    assert photos == [
        {"id": "1", "name": "bild.jpg"},
        {"id": "3", "name": "icon.PNG"},
    ]
    assert dummy_client.calls[0][1] == "/users/user-42/drive/items/folder-123/children"


def test_upload_photo_to_onedrive_uses_graph_content_endpoint(monkeypatch) -> None:
    dummy_client = _DummyClient("/drives/drive-007")
    monkeypatch.setattr(photo, "get_graph_client", lambda: dummy_client)
    monkeypatch.setattr(
        photo.st,
        "secrets",
        {"onedrive": {"folder_path": "Documents/9 Freunde"}},
    )

    result = photo.upload_photo_to_onedrive(b"test", "upload.jpg")

    assert result == {"id": "new-id", "name": "upload.jpg"}
    assert dummy_client.calls[0][0] == "PUT"
    assert (
        dummy_client.calls[0][1]
        == "/drives/drive-007/root:/Documents/9 Freunde/upload.jpg:/content"
    )


def test_download_photo_from_onedrive_returns_bytes(monkeypatch) -> None:
    dummy_client = _DummyClient()
    monkeypatch.setattr(photo, "get_graph_client", lambda: dummy_client)

    payload = photo.download_photo_from_onedrive("item-42")

    assert payload == b"binary-image"
    assert dummy_client.calls[0][1] == "/users/user-42/drive/items/item-42/content"
