from __future__ import annotations

from types import SimpleNamespace

import pytest

import onedrive_auth


def test_load_config_requires_keys(monkeypatch) -> None:
    monkeypatch.setattr(onedrive_auth.st, "secrets", {"onedrive": {"client_id": "abc"}})

    with pytest.raises(onedrive_auth.OneDriveAuthError):
        onedrive_auth.get_graph_client()


def test_load_config_requires_target_drive_identifier(monkeypatch) -> None:
    monkeypatch.setattr(
        onedrive_auth.st,
        "secrets",
        {
            "onedrive": {
                "client_id": "abc",
                "client_secret": "secret",
                "tenant_id": "tenant",
            }
        },
    )

    with pytest.raises(onedrive_auth.OneDriveAuthError) as exc_info:
        onedrive_auth.get_graph_client()

    assert exc_info.value.reason == "config"


def test_graph_client_uses_users_drive_base_path(monkeypatch) -> None:
    monkeypatch.setattr(
        onedrive_auth.msal,
        "ConfidentialClientApplication",
        lambda **_kwargs: object(),
    )
    client = onedrive_auth.GraphClient(
        onedrive_auth.OneDriveAuthConfig(
            client_id="client",
            client_secret="secret",
            tenant_id="tenant",
            drive_user_id="user-123",
            drive_id=None,
        )
    )

    assert client.drive_base_path == "/users/user-123/drive"


def test_graph_client_prefers_drive_id_base_path(monkeypatch) -> None:
    monkeypatch.setattr(
        onedrive_auth.msal,
        "ConfidentialClientApplication",
        lambda **_kwargs: object(),
    )
    client = onedrive_auth.GraphClient(
        onedrive_auth.OneDriveAuthConfig(
            client_id="client",
            client_secret="secret",
            tenant_id="tenant",
            drive_user_id="user-123",
            drive_id="drive-456",
        )
    )

    assert client.drive_base_path == "/drives/drive-456"


def test_get_onedrive_folder_requires_non_empty_path() -> None:
    with pytest.raises(onedrive_auth.OneDriveAuthError):
        onedrive_auth.get_onedrive_folder(" ")


def test_get_onedrive_folder_uses_app_compatible_endpoint(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    class _Client:
        drive_base_path = "/users/user-123/drive"

        def request(self, method: str, path: str) -> SimpleNamespace:
            calls.append((method, path))
            return SimpleNamespace(
                json=lambda: {
                    "id": "folder-id",
                    "name": "Documents",
                    "webUrl": "https://example.org",
                }
            )

    monkeypatch.setattr(onedrive_auth, "get_graph_client", lambda: _Client())

    folder = onedrive_auth.get_onedrive_folder("Documents/9 Freunde")

    assert folder.id == "folder-id"
    assert calls == [("GET", "/users/user-123/drive/root:/Documents/9 Freunde")]
