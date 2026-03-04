from __future__ import annotations

import pytest

import onedrive_auth


def test_load_config_requires_keys(monkeypatch) -> None:
    monkeypatch.setattr(onedrive_auth.st, "secrets", {"onedrive": {"client_id": "abc"}})

    with pytest.raises(onedrive_auth.OneDriveAuthError):
        onedrive_auth.get_graph_client()


def test_get_onedrive_folder_requires_non_empty_path() -> None:
    with pytest.raises(onedrive_auth.OneDriveAuthError):
        onedrive_auth.get_onedrive_folder(" ")
